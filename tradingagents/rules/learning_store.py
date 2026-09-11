"""Persistent, scoped research experience; no order execution or self-modifying code."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import date, datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import sqlite3
from typing import Mapping

from .short_term import WEIGHTS

ERROR_TYPES = {"industry", "flow", "relative_strength", "entry", "news", "risk",
               "sentiment", "quant_trap", "unknown"}
LESSONS = {
    "industry": "板块轮动失误：重新确认行业相对市场强度和资金扩散，避免弱板块补涨。",
    "flow": "资金判断失误：核验多日净流入持续性，区分单日脉冲与持续增量。",
    "relative_strength": "相对强度失误：核验个股是否持续强于所属行业。",
    "entry": "入场失误：等待买点与量价确认，预测上涨不能代替成交证据。",
    "news": "消息判断失误：核验来源、发布时间和利好是否已兑现。",
    "risk": "风险判断失误：重新审查公告、支撑失效和市场恐慌条件。",
    "sentiment": "情绪阶段失误：核验赚钱效应、涨跌停扩散和退潮迹象。",
    "quant_trap": "量化陷阱判断失误：核验冲高回落、价量背离和流动性骤变。",
}


def number(value):
    if isinstance(value, bool):
        return None
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (ValueError, TypeError):
        return None


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False)


def now():
    return datetime.now(timezone.utc).isoformat()


class LearningStore:
    """WAL, foreign keys, immutable observations and versioned learning policies.

    Tables use a prefix to coexist with earlier experimental learning tables.
    A scope is an API user id or 'local'; observations and policies never cross scopes.
    """

    def __init__(self, path="data/learning.db"):
        if str(path) == ":memory:":
            raise ValueError("Use a file path; learning memory must survive connection closure")
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as c:
            c.execute("PRAGMA journal_mode=WAL")
            c.executescript("""
                CREATE TABLE IF NOT EXISTS learning_predictions (
                    id INTEGER PRIMARY KEY, scope TEXT NOT NULL, run_key TEXT NOT NULL,
                    symbol TEXT NOT NULL, trade_date TEXT NOT NULL, horizon INTEGER NOT NULL,
                    reference_price REAL, reference_date TEXT, direction INTEGER,
                    action TEXT NOT NULL, features TEXT NOT NULL, evidence TEXT NOT NULL,
                    policy_id INTEGER, recorded_at TEXT NOT NULL,
                    UNIQUE(scope,run_key));
                CREATE TABLE IF NOT EXISTS learning_outcomes (
                    prediction_id INTEGER PRIMARY KEY REFERENCES learning_predictions(id),
                    realized_date TEXT NOT NULL, realized_price REAL NOT NULL,
                    stock_return REAL NOT NULL, directional_hit INTEGER, reference_price REAL NOT NULL,
                    error_type TEXT, source TEXT NOT NULL, recorded_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS learning_policies (
                    id INTEGER PRIMARY KEY, scope TEXT NOT NULL, status TEXT NOT NULL,
                    weights TEXT NOT NULL, metrics TEXT NOT NULL, fingerprint TEXT NOT NULL,
                    created_at TEXT NOT NULL, UNIQUE(scope,fingerprint));
                CREATE TABLE IF NOT EXISTS learning_events (
                    id INTEGER PRIMARY KEY, scope TEXT NOT NULL, kind TEXT NOT NULL,
                    payload TEXT NOT NULL, created_at TEXT NOT NULL);
                CREATE INDEX IF NOT EXISTS learning_pending
                    ON learning_predictions(scope,symbol,trade_date);
            """)

    @contextmanager
    def connection(self):
        c = sqlite3.connect(self.path, timeout=30)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA foreign_keys=ON")
        try:
            with c:
                yield c
        finally:
            c.close()

    def record_prediction(self, prediction: Mapping, scope="local") -> int:
        symbol = str(prediction["symbol"])
        trade_date = date.fromisoformat(prediction["trade_date"]).isoformat()
        horizon = prediction.get("horizon", 5)
        if not isinstance(horizon, int) or not 2 <= horizon <= 5:
            raise ValueError("horizon must be 2-5 trading sessions")
        action = prediction.get("action", "OBSERVE")
        if action not in {"BUY", "WAIT", "OBSERVE", "NO TRADE"}:
            raise ValueError("invalid action")
        direction = prediction.get("direction")
        if direction not in {-1, 0, 1, None}:
            raise ValueError("direction must be -1, 0, 1 or null")
        price = number(prediction.get("reference_price"))
        if prediction.get("reference_price") is not None and (price is None or price <= 0):
            raise ValueError("reference_price must be finite and positive")
        reference_date = prediction.get("reference_date")
        if reference_date is not None:
            reference_date = date.fromisoformat(reference_date).isoformat()
            if reference_date > trade_date:
                raise ValueError("reference date is in the future")
        if price is not None and reference_date != trade_date:
            raise ValueError("reference price must be from the forecast session")
        features = prediction.get("features") or {}
        if any(k not in WEIGHTS or number(v) is None or not 0 <= number(v) <= 1
               for k, v in features.items()):
            raise ValueError("features must use known factors normalized to [0,1]")
        evidence = prediction.get("evidence") or {}
        # The caller supplies a stable job id; repeated callbacks cannot rewrite predictions.
        run_key = str(prediction["run_key"])
        payload = (scope, run_key, symbol, trade_date, horizon, price, reference_date,
                   direction, action, encoded(features), encoded(evidence),
                   prediction.get("policy_id"))
        with self.connection() as c:
            old = c.execute("SELECT * FROM learning_predictions WHERE scope=? AND run_key=?",
                            (scope, run_key)).fetchone()
            if old:
                fields = ("scope", "run_key", "symbol", "trade_date", "horizon", "reference_price",
                          "reference_date", "direction", "action", "features", "evidence", "policy_id")
                if tuple(old[k] for k in fields) != payload:
                    raise ValueError("prediction is immutable; use a new run_key for a new analysis")
                return old["id"]
            row = c.execute("""INSERT INTO learning_predictions
                (scope,run_key,symbol,trade_date,horizon,reference_price,reference_date,direction,
                 action,features,evidence,policy_id,recorded_at)
                 VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""", (*payload, now()))
            return row.lastrowid

    def pending(self, scope="local", symbol=None):
        with self.connection() as c:
            rows = c.execute("""SELECT p.* FROM learning_predictions p
                LEFT JOIN learning_outcomes o ON o.prediction_id=p.id
                WHERE p.scope=? AND o.prediction_id IS NULL
                AND (? IS NULL OR p.symbol=?) ORDER BY p.trade_date,p.id""",
                             (scope, symbol, symbol)).fetchall()
        return [dict(r) for r in rows]

    def record_outcome(self, prediction_id, *, realized_price, realized_date,
                       session_dates, source, scope="local", error_type=None, reference_price=None):
        """Review a fixed horizon using an explicit exchange-session calendar.

        A price-only review measures forecast direction. WAIT/OBSERVE/NO TRADE
        are never represented as filled trades or strategy P&L.
        """
        price = number(realized_price)
        realized_date = date.fromisoformat(realized_date).isoformat()
        sessions = sorted(set(date.fromisoformat(d).isoformat() for d in session_dates))
        if price is None or price <= 0 or not str(source).strip():
            raise ValueError("positive realized price and source are required")
        if error_type is not None and error_type not in ERROR_TYPES:
            raise ValueError("unknown error type")
        with self.connection() as c:
            c.execute("BEGIN IMMEDIATE")
            p = c.execute("SELECT * FROM learning_predictions WHERE id=? AND scope=?",
                          (prediction_id, scope)).fetchone()
            if p is None:
                raise KeyError(prediction_id)
            eligible = [d for d in sessions if d > p["trade_date"]]
            if len(eligible) < p["horizon"] or eligible[p["horizon"] - 1] != realized_date:
                raise ValueError("outcome must match the prediction's trading-session horizon")
            baseline = p["reference_price"] if p["reference_price"] is not None else number(reference_price)
            if baseline is None or baseline <= 0:
                raise ValueError("missing reference price; do not fabricate a baseline")
            stock_return = price / baseline - 1
            direction = p["direction"]
            hit = int(stock_return * direction > 0) if direction in {-1, 1} else None
            error_type = (error_type or "unknown") if hit == 0 else None
            old = c.execute("SELECT * FROM learning_outcomes WHERE prediction_id=?",
                            (prediction_id,)).fetchone()
            if old:
                if (old["realized_date"], old["realized_price"], old["error_type"], old["reference_price"]) != (
                        realized_date, price, error_type, baseline):
                    raise ValueError("outcome is immutable; review the data provenance")
                return dict(old)
            c.execute("""INSERT INTO learning_outcomes VALUES(?,?,?,?,?,?,?,?,?)""",
                      (prediction_id, realized_date, price, stock_return, hit, baseline, error_type,
                       str(source), now()))
            self._event(c, scope, "review", {"prediction_id": prediction_id, "hit": hit,
                                           "error_type": error_type})
        # Learning is transactional and deduplicated independently of callbacks.
        self.evolve(scope=scope)
        return {"prediction_id": prediction_id, "stock_return": stock_return,
                "directional_hit": hit, "error_type": error_type}

    @staticmethod
    def _event(c, scope, kind, payload):
        c.execute("INSERT INTO learning_events(scope,kind,payload,created_at) VALUES(?,?,?,?)",
                  (scope, kind, encoded(payload), now()))

    def policy(self, scope="local", as_of=None):
        with self.connection() as c:
            row = c.execute("""SELECT * FROM learning_policies WHERE scope=? AND status IN
                ('active','retired') AND (? IS NULL OR created_at<?)
                ORDER BY id DESC LIMIT 1""", (scope, as_of, as_of)).fetchone()
        if row:
            return {"id": row["id"], "weights": json.loads(row["weights"]),
                    "metrics": json.loads(row["metrics"])}
        return {"id": None, "weights": dict(WEIGHTS), "metrics": {}}

    def evolve(self, scope="local"):
        """Evaluate a bounded challenger on later dates; never learn from LLM praise.

        Train on the older 70% of dates, validate on later, non-overlapping outcomes.
        Up to one sample per symbol/session; repeated runs do not inflate evidence.
        """
        with self.connection() as c:
            c.execute("BEGIN IMMEDIATE")
            rows = c.execute("""SELECT p.*,o.stock_return,o.realized_date
                FROM learning_predictions p JOIN learning_outcomes o ON p.id=o.prediction_id
                WHERE p.scope=? ORDER BY p.trade_date,p.id""", (scope,)).fetchall()
            distinct = {}
            for r in rows:
                if r["horizon"] != 5 or r["recorded_at"][:10] > r["trade_date"]:
                    continue
                features = json.loads(r["features"])
                if set(features) == set(WEIGHTS):
                    distinct.setdefault((r["symbol"], r["trade_date"]), (dict(r), features))
            samples = list(distinct.values())
            dates = sorted({r["trade_date"] for r, _ in samples})
            if len(samples) < 60 or len(dates) < 20:
                return {"status": "insufficient_samples", "samples": len(samples), "dates": len(dates)}
            split = dates[int(len(dates) * .7)]
            train = [(r, f) for r, f in samples if r["realized_date"] < split]
            validation = [(r, f) for r, f in samples if r["trade_date"] >= split]
            if len(train) < 30 or len(validation) < 15:
                return {"status": "insufficient_purged_samples"}
            # Once a validation block has promoted a policy, only newer data can
            # validate the next challenger. Prevent repeated tuning on one holdout.
            active = c.execute("""SELECT * FROM learning_policies WHERE scope=? AND status='active'
                ORDER BY id DESC LIMIT 1""", (scope,)).fetchone()
            current = json.loads(active["weights"]) if active else dict(WEIGHTS)
            if active:
                last_end = json.loads(active["metrics"]).get("validation_end", "0000-01-01")
                validation = [(r, f) for r, f in validation if r["trade_date"] > last_end]
                if len(validation) < 15:
                    return {"status": "waiting_for_new_validation"}
            fingerprint = hashlib.sha256(encoded([
                (r["id"], r["stock_return"]) for r, _ in samples
            ]).encode()).hexdigest()
            if c.execute("SELECT 1 FROM learning_policies WHERE scope=? AND fingerprint=?",
                         (scope, fingerprint)).fetchone():
                return {"status": "already_evaluated"}
            raw = {}
            for k, base in WEIGHTS.items():
                positives = [f[k] for r, f in train if r["stock_return"] > 0]
                negatives = [f[k] for r, f in train if r["stock_return"] <= 0]
                separation = (sum(positives) / len(positives) - sum(negatives) / len(negatives)
                              if positives and negatives else 0)
                # Center factor effects rather than crediting every factor for every win.
                raw[k] = base * (1 + .2 * max(-1, min(1, separation)))
            scale = 100 / sum(raw.values())
            proposal = {k: .8 * current[k] + .2 * raw[k] * scale for k in WEIGHTS}
            bounded = all(.8 * WEIGHTS[k] <= proposal[k] <= 1.2 * WEIGHTS[k] for k in WEIGHTS)
            def loss(weights):
                return sum((sum(f[k] * weights[k] for k in WEIGHTS) / 100 -
                            int(r["stock_return"] > 0)) ** 2 for r, f in validation) / len(validation)
            old_loss, new_loss = loss(current), loss(proposal)
            accepted = bounded and new_loss < old_loss - .001
            metrics = {"train_samples": len(train), "validation_samples": len(validation),
                       "validation_start": min(r["trade_date"] for r, _ in validation),
                       "validation_end": max(r["trade_date"] for r, _ in validation),
                       "baseline_brier": old_loss, "challenger_brier": new_loss,
                       "bounded": bounded, "scope": scope}
            if accepted:
                c.execute("UPDATE learning_policies SET status='retired' WHERE scope=? AND status='active'",
                          (scope,))
            c.execute("""INSERT INTO learning_policies(scope,status,weights,metrics,fingerprint,created_at)
                VALUES(?,?,?,?,?,?)""", (scope, "active" if accepted else "rejected",
                                        encoded(proposal), encoded(metrics), fingerprint, now()))
            self._event(c, scope, "policy_promoted" if accepted else "policy_rejected", metrics)
            return {"status": "promoted" if accepted else "rejected", **metrics}

    def snapshot(self, scope="local", as_of=None):
        with self.connection() as c:
            rows = c.execute("""SELECT p.*,o.directional_hit,o.error_type,o.realized_date,o.recorded_at AS outcome_recorded_at
                FROM learning_predictions p LEFT JOIN learning_outcomes o ON p.id=o.prediction_id
                WHERE p.scope=? AND (? IS NULL OR p.trade_date<?)
                AND (? IS NULL OR p.recorded_at<?)""", (scope, as_of, as_of, as_of, as_of)).fetchall()
            # Keep both raw count and deduplicated forecast accuracy explicit.
        unique = {}
        for r in rows:
            if r["realized_date"] and (as_of is None or (r["realized_date"] < as_of and r["outcome_recorded_at"] < as_of)):
                unique.setdefault((r["symbol"], r["trade_date"], r["horizon"]), r)
        scored = [r for r in unique.values() if r["directional_hit"] is not None]
        hits = sum(r["directional_hit"] for r in scored)
        errors = {}
        for r in scored:
            if r["directional_hit"] == 0:
                k = r["error_type"] or "unknown"
                errors[k] = errors.get(k, 0) + 1
        return {"predictions": len(rows), "resolved": len(unique), "directional_samples": len(scored),
                "directional_hits": hits, "directional_hit_rate": hits / len(scored) if scored else None,
                "error_types": errors, "policy": self.policy(scope, as_of),
                "metric": "forecast_direction_not_trade_pnl"}

    def lessons(self, scope="local", as_of=None):
        snap = self.snapshot(scope, as_of)
        return [{"error_type": k, "samples": count, "guidance": LESSONS[k]}
                for k, count in sorted(snap["error_types"].items(), key=lambda x: -x[1])
                if k in LESSONS and count >= 3]

