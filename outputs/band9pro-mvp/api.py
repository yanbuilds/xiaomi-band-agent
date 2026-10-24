"""Single-user API prototype. Run behind HTTPS for remote access.

PHONE_TOKEN and AGENT_TOKEN are independent random bearer secrets, not band keys.
Agent pulls pending events, then posts a result; phone polls notifications.
"""
import hmac
import json
import os
import sqlite3
import time
from contextlib import closing
from typing import Literal
from fastapi import FastAPI, Header, HTTPException, Query
from pydantic import BaseModel, Field, model_validator
from state_engine import infer_state, possible_oversleep

app = FastAPI(title='Band local bridge MVP')
DB = os.environ.get('BAND_DB', 'band.sqlite3')


def db():
    c = sqlite3.connect(DB, timeout=15)
    c.execute('CREATE TABLE IF NOT EXISTS events (id TEXT PRIMARY KEY, body TEXT NOT NULL, result TEXT, expires INTEGER, delivered INTEGER DEFAULT 0)')
    c.execute('CREATE TABLE IF NOT EXISTS health_events (id TEXT PRIMARY KEY, body TEXT NOT NULL)')
    c.execute('CREATE TABLE IF NOT EXISTS interactions (id TEXT PRIMARY KEY, body TEXT NOT NULL, created INTEGER NOT NULL)')
    c.commit()
    return c


def authorize(role, header):
    token = os.environ.get(role + '_TOKEN', '')
    if len(token) < 24:
        raise HTTPException(503, 'server token not configured')
    if not hmac.compare_digest(header or '', 'Bearer ' + token):
        raise HTTPException(401, 'unauthorized')


class Stage(BaseModel):
    start: int
    end: int
    raw_code: int = Field(ge=0, le=255)
    stage: Literal['deep','light','rem','awake','unknown']


class Sleep(BaseModel):
    start: int = Field(gt=0)
    end: int = Field(gt=0)
    total_minutes: int = Field(gt=0, le=2880)
    deep_minutes: int = Field(ge=0, le=2880)
    light_minutes: int = Field(ge=0, le=2880)
    rem_minutes: int = Field(ge=0, le=2880)
    awake_minutes: int = Field(ge=0, le=2880)
    stages: list[Stage] = Field(max_length=3000)

    @model_validator(mode='after')
    def validate_intervals(self):
        if not 0 < self.end-self.start <= 172800:
            raise ValueError('invalid sleep interval')
        previous = self.start
        for s in self.stages:
            if not previous <= s.start < s.end <= self.end:
                raise ValueError('invalid/overlapping stages')
            previous = s.end
        return self


class Event(BaseModel):
    schema_version: Literal[1]
    device_id: str = Field(min_length=1, max_length=64)
    event_id: str = Field(pattern=r'^[a-f0-9]{64}$')
    source: dict
    sleep: Sleep


class HealthSample(BaseModel):
    timestamp: int = Field(gt=0)
    metric: Literal['heart_rate', 'steps', 'spo2']
    value: float = Field(ge=0)
    unit: Literal['bpm', 'count', 'percent']

    @model_validator(mode='after')
    def validate_metric(self):
        limits = {
            'heart_rate': ('bpm', 30, 260),
            'steps': ('count', 0, 200000),
            'spo2': ('percent', 50, 100),
        }
        unit, low, high = limits[self.metric]
        if self.unit != unit or not low <= self.value <= high:
            raise ValueError('metric value/unit out of range')
        return self


class HealthEvent(BaseModel):
    schema_version: Literal[1]
    device_id: str = Field(min_length=1, max_length=64)
    event_id: str = Field(pattern=r'^[a-f0-9]{64}$')
    source: dict
    samples: list[HealthSample] = Field(min_length=1, max_length=20000)


class StateEvaluationRequest(BaseModel):
    now: int = Field(gt=0)
    samples: list[HealthSample] = Field(default_factory=list, max_length=20000)
    sleep: dict | None = None
    latest_wake_at: int | None = Field(default=None, gt=0)
    workday: bool = True
    resting_heart_rate: float | None = Field(default=None, ge=30, le=200)


class Option(BaseModel):
    id: str = Field(min_length=1, max_length=32)
    text: str = Field(min_length=1, max_length=60)


class Result(BaseModel):
    title: str = Field(min_length=1, max_length=40)
    text: str = Field(min_length=1, max_length=160)
    options: list[Option] = Field(max_length=3)
    expires_at: int


class Interaction(BaseModel):
    request_id: str = Field(min_length=1, max_length=128)
    kind: Literal['option_selected', 'voice_request']
    option_id: str | None = Field(default=None, max_length=32)
    text: str | None = Field(default=None, max_length=2000)

    @model_validator(mode='after')
    def validate_payload(self):
        if self.kind == 'option_selected' and not self.option_id:
            raise ValueError('option_id required for option_selected')
        if self.kind == 'voice_request' and self.option_id:
            raise ValueError('option_id not allowed for voice_request')
        return self


@app.post('/v1/sleep')
def ingest(event: Event, authorization: str | None = Header(default=None)):
    authorize('PHONE', authorization)
    body = json.dumps(event.model_dump(), sort_keys=True, ensure_ascii=False)
    if len(body.encode()) > 512000:
        raise HTTPException(413, 'event too large')
    with closing(db()) as c, c:
        c.execute('INSERT OR IGNORE INTO events(id,body) VALUES (?,?)', (event.event_id,body))
        old = c.execute('SELECT body FROM events WHERE id=?', (event.event_id,)).fetchone()[0]
        if old != body:
            raise HTTPException(409, 'event ID reused with different data')
    return {'event_id': event.event_id, 'stored': True}


@app.post('/v1/health')
def ingest_health(event: HealthEvent, authorization: str | None = Header(default=None)):
    authorize('PHONE', authorization)
    body = json.dumps(event.model_dump(), sort_keys=True, ensure_ascii=False)
    if len(body.encode()) > 512000:
        raise HTTPException(413, 'event too large')
    with closing(db()) as c, c:
        c.execute('INSERT OR IGNORE INTO health_events(id,body) VALUES (?,?)',
                  (event.event_id, body))
        old = c.execute('SELECT body FROM health_events WHERE id=?',
                        (event.event_id,)).fetchone()[0]
        if old != body:
            raise HTTPException(409, 'event ID reused with different data')
    return {'event_id': event.event_id, 'stored': True}


@app.get('/v1/agent/pending')
def pending(authorization: str | None = Header(default=None),
            limit: int = Query(default=20, ge=1, le=20)):
    authorize('AGENT', authorization)
    with closing(db()) as c:
        return [json.loads(r[0]) for r in c.execute(
            'SELECT body FROM events WHERE result IS NULL ORDER BY rowid LIMIT ?', (limit,))]


@app.get('/v1/agent/health/pending')
def health_pending(authorization: str | None = Header(default=None),
                   limit: int = Query(default=20, ge=1, le=20)):
    authorize('AGENT', authorization)
    with closing(db()) as c:
        return [json.loads(r[0]) for r in c.execute(
            'SELECT body FROM health_events ORDER BY rowid LIMIT ?', (limit,))]


@app.post('/v1/state/evaluate')
def evaluate_state(request: StateEvaluationRequest, authorization: str | None = Header(default=None)):
    authorize('PHONE', authorization)
    samples = [sample.model_dump() for sample in request.samples]
    state = infer_state(now=request.now, samples=samples, sleep=request.sleep,
                        resting_heart_rate=request.resting_heart_rate)
    alert = possible_oversleep(now=request.now, latest_wake_at=request.latest_wake_at,
                               state=state, workday=request.workday)
    return {'state': state.as_dict(), 'alert': alert}


@app.post('/v1/agent/results/{event_id}')
def result(event_id: str, result: Result, authorization: str | None = Header(default=None)):
    authorize('AGENT', authorization)
    if not time.time() < result.expires_at <= time.time()+86400:
        raise HTTPException(422, 'expiry must be within the next day')
    if len({x.id for x in result.options}) != len(result.options):
        raise HTTPException(422, 'duplicate option IDs')
    body = json.dumps(result.model_dump(), sort_keys=True, ensure_ascii=False)
    with closing(db()) as c, c:
        row = c.execute('SELECT result FROM events WHERE id=?', (event_id,)).fetchone()
        if not row:
            raise HTTPException(404, 'event not found')
        if row[0] and row[0] != body:
            raise HTTPException(409, 'immutable result already exists')
        c.execute('UPDATE events SET result=?, expires=? WHERE id=?', (body,result.expires_at,event_id))
    return {'notification_id': event_id}


@app.get('/v1/notifications')
def notifications(authorization: str | None = Header(default=None)):
    authorize('PHONE', authorization)
    with closing(db()) as c:
        return [dict(notification_id=r[0], device_id=json.loads(r[1])['device_id'],
                     **json.loads(r[2])) for r in c.execute(
            'SELECT id,body,result FROM events WHERE result IS NOT NULL AND delivered=0 AND expires>? ORDER BY rowid LIMIT 20', (int(time.time()),))]


@app.post('/v1/notifications/{event_id}/submitted')
def submitted(event_id: str, authorization: str | None = Header(default=None)):
    # This means submitted to the local Bluetooth send queue, NOT read or selected.
    authorize('PHONE', authorization)
    with closing(db()) as c, c:
        cur = c.execute('UPDATE events SET delivered=1 WHERE id=? AND result IS NOT NULL', (event_id,))
        if not cur.rowcount:
            raise HTTPException(404, 'notification not found')
    return {'status': 'submitted_to_local_queue'}


@app.post('/v1/interactions')
def interaction(request: Interaction, authorization: str | None = Header(default=None)):
    """Persist a watch click/voice request for the Agent conversation loop."""
    authorize('PHONE', authorization)
    body = json.dumps(request.model_dump(), sort_keys=True, ensure_ascii=False)
    interaction_id = hmac.new(b'band-interaction-v1', body.encode(), 'sha256').hexdigest()
    with closing(db()) as c, c:
        c.execute('INSERT OR IGNORE INTO interactions(id,body,created) VALUES (?,?,?)',
                  (interaction_id, body, int(time.time())))
    return {'interaction_id': interaction_id, 'stored': True}


@app.get('/v1/agent/interactions')
def pending_interactions(authorization: str | None = Header(default=None),
                         limit: int = Query(default=20, ge=1, le=100)):
    authorize('AGENT', authorization)
    with closing(db()) as c:
        return [dict(interaction_id=r[0], **json.loads(r[1]), created=r[2])
                for r in c.execute('SELECT id,body,created FROM interactions ORDER BY created LIMIT ?', (limit,))]
