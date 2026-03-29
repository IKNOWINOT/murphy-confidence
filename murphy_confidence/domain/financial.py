# Copyright © 2020-2026 Inoni Limited Liability Company. All rights reserved.
# Created by: Corey Post

"""
murphy_confidence.domain.financial
====================================
Financial compliance sub-models that close the six vertical testing gaps:

1. Real-time market liquidity data integrated into D(x) domain score
2. Cross-border regulatory mapping (MiFID II vs. SEC)
3. Wash-trade pattern detection dedicated hazard sub-model
4. Counterparty credit risk scoring with live data interface
5. Intraday position limits wired to budget gate thresholds
6. Dark pool order routing compliance rules

Each sub-model computes a specialised score in [0, 1] that feeds into the
MFGC formula as part of the G(x), D(x), or H(x) component.

Zero external dependencies.
"""

from __future__ import annotations

import hashlib
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, FrozenSet, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Constants & validation
# ---------------------------------------------------------------------------

_TRADE_ID_RE = re.compile(r"^[A-Za-z0-9_\-]{1,100}$")
_INSTRUMENT_ID_RE = re.compile(r"^[A-Za-z0-9_.\-]{1,100}$")
_COUNTERPARTY_RE = re.compile(r"^[A-Za-z0-9_\-]{1,200}$")
_MAX_TRADES = 100_000
_MAX_POSITION_ENTRIES = 50_000

_JURISDICTIONS: FrozenSet[str] = frozenset({
    "US_SEC", "EU_MIFID2", "UK_FCA", "JP_FSA", "SG_MAS",
    "HK_SFC", "AU_ASIC", "CA_CSA", "CH_FINMA",
})


def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, float(v)))


def _validate_trade_id(tid: str) -> str:
    if not isinstance(tid, str) or not _TRADE_ID_RE.match(tid):
        raise ValueError(f"Invalid trade_id: must match {_TRADE_ID_RE.pattern}")
    return tid


def _validate_instrument_id(iid: str) -> str:
    if not isinstance(iid, str) or not _INSTRUMENT_ID_RE.match(iid):
        raise ValueError(f"Invalid instrument_id: must match {_INSTRUMENT_ID_RE.pattern}")
    return iid


def _validate_counterparty(cpid: str) -> str:
    if not isinstance(cpid, str) or not _COUNTERPARTY_RE.match(cpid):
        raise ValueError(f"Invalid counterparty_id: must match {_COUNTERPARTY_RE.pattern}")
    return cpid


# ---------------------------------------------------------------------------
# 1. Market Liquidity Scorer
# ---------------------------------------------------------------------------

@dataclass
class LiquiditySnapshot:
    """Point-in-time liquidity data for an instrument."""
    instrument_id: str
    bid_ask_spread_bps: float   # Basis points
    depth_lots: float           # Order book depth
    volume_24h: float           # 24-hour trading volume
    volatility_pct: float       # Annualised volatility %
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        _validate_instrument_id(self.instrument_id)
        if self.bid_ask_spread_bps < 0:
            raise ValueError("bid_ask_spread_bps must be non-negative")
        if self.depth_lots < 0:
            raise ValueError("depth_lots must be non-negative")


class MarketLiquidityScorer:
    """
    Computes a domain sub-score D_liquidity(x) based on real-time market data.

    Higher liquidity → higher domain confidence that the trade can execute
    without adverse market impact.

    Closes gap: *Real-time market liquidity data not integrated into D(x)*
    """

    def __init__(self) -> None:
        self._snapshots: Dict[str, LiquiditySnapshot] = {}

    def update_snapshot(self, snapshot: LiquiditySnapshot) -> None:
        self._snapshots[snapshot.instrument_id] = snapshot

    def get_snapshot(self, instrument_id: str) -> Optional[LiquiditySnapshot]:
        return self._snapshots.get(_validate_instrument_id(instrument_id))

    def score(self, instrument_id: str, trade_size: float = 0.0) -> float:
        """
        Compute D_liquidity(x) ∈ [0, 1].

        Factors: bid-ask spread, order book depth, volume, volatility.
        A larger trade_size relative to depth reduces the score.
        """
        snap = self.get_snapshot(instrument_id)
        if snap is None:
            return 0.5  # No data → conservative

        # Spread score: tight spread = good (100 bps = 0, 0 bps = 1)
        spread_score = _clamp(1.0 - snap.bid_ask_spread_bps / 100.0)

        # Depth score: can we fill without moving the market?
        if snap.depth_lots > 0 and trade_size > 0:
            depth_ratio = trade_size / snap.depth_lots
            depth_score = _clamp(1.0 - depth_ratio)
        else:
            depth_score = 0.7 if snap.depth_lots > 0 else 0.3

        # Volume score (log-scaled, saturates at 1M)
        import math
        volume_score = _clamp(math.log1p(snap.volume_24h) / math.log1p(1_000_000))

        # Volatility penalty (high vol = less predictable execution)
        vol_penalty = _clamp(snap.volatility_pct / 100.0)

        return _clamp(
            0.30 * spread_score + 0.25 * depth_score
            + 0.25 * volume_score - 0.20 * vol_penalty
        )


# ---------------------------------------------------------------------------
# 2. Cross-Border Regulatory Mapper
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RegulatoryRule:
    """A single regulatory rule mapping."""
    jurisdiction: str
    rule_id: str
    title: str
    requirement: str
    murphy_gate: str    # Which gate type enforces this
    threshold: float    # Minimum confidence threshold
    blocking: bool = True

    def __post_init__(self) -> None:
        if self.jurisdiction not in _JURISDICTIONS:
            raise ValueError(f"Unknown jurisdiction: {self.jurisdiction}")


class RegulatoryMapper:
    """
    Maps cross-border regulatory requirements (MiFID II, SEC, etc.) to
    Murphy safety gates and confidence thresholds.

    Closes gap: *Cross-border regulatory mapping (MiFID II vs. SEC) incomplete*
    """

    def __init__(self) -> None:
        self._rules: Dict[str, List[RegulatoryRule]] = {}
        self._load_default_rules()

    def _load_default_rules(self) -> None:
        defaults = [
            RegulatoryRule("US_SEC", "SEC-10b5", "Anti-Fraud", "Prohibit deceptive acts in securities transactions", "COMPLIANCE", 0.90, True),
            RegulatoryRule("US_SEC", "SEC-15c3", "Net Capital", "Maintain minimum net capital requirements", "BUDGET", 0.85, True),
            RegulatoryRule("US_SEC", "SEC-SHO", "Reg SHO", "Short selling locate and close-out requirements", "COMPLIANCE", 0.88, True),
            RegulatoryRule("EU_MIFID2", "MIFID-ALGO", "Algo Trading", "Algorithm testing, kill switches, and market-making obligations", "EXECUTIVE", 0.92, True),
            RegulatoryRule("EU_MIFID2", "MIFID-BEST", "Best Execution", "Obtain best possible result for client orders", "QA", 0.80, False),
            RegulatoryRule("EU_MIFID2", "MIFID-TRANS", "Pre/Post Trade Transparency", "Publication of bid/offer prices and transaction reports", "COMPLIANCE", 0.85, True),
            RegulatoryRule("EU_MIFID2", "MIFID-POS", "Position Limits", "Commodity derivatives position limits enforcement", "BUDGET", 0.80, True),
            RegulatoryRule("UK_FCA", "FCA-COND", "Conduct Rules", "Treat customers fairly and manage conflicts of interest", "COMPLIANCE", 0.88, True),
            RegulatoryRule("UK_FCA", "FCA-ALGO", "Algo Oversight", "Algorithmic trading systems oversight and controls", "EXECUTIVE", 0.90, True),
        ]
        for rule in defaults:
            self.add_rule(rule)

    def add_rule(self, rule: RegulatoryRule) -> None:
        self._rules.setdefault(rule.jurisdiction, []).append(rule)

    def get_rules(self, jurisdiction: str) -> List[RegulatoryRule]:
        if jurisdiction not in _JURISDICTIONS:
            raise ValueError(f"Unknown jurisdiction: {jurisdiction}")
        return self._rules.get(jurisdiction, [])

    def get_applicable_rules(self, jurisdictions: List[str]) -> List[RegulatoryRule]:
        """Get all rules applicable across multiple jurisdictions."""
        rules: List[RegulatoryRule] = []
        for j in jurisdictions:
            rules.extend(self.get_rules(j))
        return rules

    def score(self, jurisdictions: List[str], confidence_score: float) -> float:
        """
        Compute regulatory compliance domain score D_reg(x) ∈ [0, 1].

        Higher score when confidence exceeds all applicable thresholds.
        """
        rules = self.get_applicable_rules(jurisdictions)
        if not rules:
            return 0.5  # No rules → conservative

        passed = sum(1 for r in rules if confidence_score >= r.threshold)
        return _clamp(passed / len(rules))


# ---------------------------------------------------------------------------
# 3. Wash-Trade Pattern Detector
# ---------------------------------------------------------------------------

@dataclass
class TradeRecord:
    """A single trade record for pattern analysis."""
    trade_id: str
    instrument_id: str
    side: str           # "BUY" | "SELL"
    quantity: float
    price: float
    timestamp: datetime
    account_id: str
    venue: str = "PRIMARY"

    def __post_init__(self) -> None:
        _validate_trade_id(self.trade_id)
        _validate_instrument_id(self.instrument_id)
        if self.side not in ("BUY", "SELL"):
            raise ValueError("side must be 'BUY' or 'SELL'")
        if self.quantity <= 0:
            raise ValueError("quantity must be positive")
        if self.price <= 0:
            raise ValueError("price must be positive")


class WashTradeDetector:
    """
    Detects wash-trade patterns (same beneficial owner buying and selling
    to themselves to create misleading market activity).

    Computes a hazard sub-score H_wash(x) that increases when suspicious
    patterns are detected.

    Closes gap: *Wash-trade pattern detection requires dedicated hazard sub-model*
    """

    def __init__(self, time_window_seconds: int = 300, price_tolerance_pct: float = 0.5) -> None:
        self._trades: List[TradeRecord] = []
        self._time_window = max(1, time_window_seconds)
        self._price_tolerance = max(0.0, price_tolerance_pct)

    @property
    def trade_count(self) -> int:
        return len(self._trades)

    def add_trade(self, trade: TradeRecord) -> None:
        if len(self._trades) >= _MAX_TRADES:
            # Evict oldest 10%
            evict_count = _MAX_TRADES // 10
            self._trades = self._trades[evict_count:]
        self._trades.append(trade)

    def detect_patterns(self, account_id: str, instrument_id: str) -> List[Dict[str, Any]]:
        """
        Find wash-trade patterns: matching buy/sell pairs from the same
        account within the time window at similar prices.
        """
        acct = account_id
        inst = _validate_instrument_id(instrument_id)
        relevant = [
            t for t in self._trades
            if t.account_id == acct and t.instrument_id == inst
        ]

        patterns: List[Dict[str, Any]] = []
        buys = [t for t in relevant if t.side == "BUY"]
        sells = [t for t in relevant if t.side == "SELL"]

        for buy in buys:
            for sell in sells:
                if buy.trade_id == sell.trade_id:
                    continue
                time_diff = abs((buy.timestamp - sell.timestamp).total_seconds())
                if time_diff > self._time_window:
                    continue
                price_diff_pct = abs(buy.price - sell.price) / buy.price * 100
                if price_diff_pct <= self._price_tolerance:
                    qty_match = min(buy.quantity, sell.quantity) / max(buy.quantity, sell.quantity)
                    patterns.append({
                        "buy_trade": buy.trade_id,
                        "sell_trade": sell.trade_id,
                        "time_diff_sec": round(time_diff, 1),
                        "price_diff_pct": round(price_diff_pct, 4),
                        "quantity_match": round(qty_match, 4),
                        "confidence": round(qty_match * (1 - price_diff_pct / self._price_tolerance) if self._price_tolerance > 0 else qty_match, 4),
                    })
        return patterns

    def score(self, account_id: str, instrument_id: str) -> float:
        """
        Compute wash-trade hazard sub-score H_wash(x) ∈ [0, 1].

        Higher score = more suspicious patterns detected.
        """
        patterns = self.detect_patterns(account_id, instrument_id)
        if not patterns:
            return 0.0

        # Aggregate confidence of detected patterns (noisy-OR)
        p_no_wash = 1.0
        for p in patterns:
            p_no_wash *= (1.0 - _clamp(p["confidence"]))
        return _clamp(1.0 - p_no_wash)


# ---------------------------------------------------------------------------
# 4. Counterparty Credit Risk Scorer
# ---------------------------------------------------------------------------

@dataclass
class CreditProfile:
    """Counterparty credit risk profile."""
    counterparty_id: str
    credit_rating: str      # "AAA" | "AA" | "A" | "BBB" | "BB" | "B" | "CCC" | "D"
    exposure_usd: float
    collateral_usd: float
    pd_1y: float            # 1-year probability of default [0, 1]
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        _validate_counterparty(self.counterparty_id)
        valid_ratings = ("AAA", "AA", "A", "BBB", "BB", "B", "CCC", "D")
        if self.credit_rating not in valid_ratings:
            raise ValueError(f"Invalid credit_rating: {self.credit_rating}")
        if not 0.0 <= self.pd_1y <= 1.0:
            raise ValueError("pd_1y must be in [0, 1]")


_RATING_PD: Dict[str, float] = {
    "AAA": 0.0001, "AA": 0.001, "A": 0.005, "BBB": 0.02,
    "BB": 0.05, "B": 0.10, "CCC": 0.25, "D": 1.0,
}


class CounterpartyCreditScorer:
    """
    Computes counterparty credit risk domain score using live credit profiles
    instead of static proxies.

    Closes gap: *Counterparty credit risk scoring uses static proxy — not live data*
    """

    def __init__(self) -> None:
        self._profiles: Dict[str, CreditProfile] = {}

    def update_profile(self, profile: CreditProfile) -> None:
        self._profiles[profile.counterparty_id] = profile

    def get_profile(self, counterparty_id: str) -> Optional[CreditProfile]:
        return self._profiles.get(_validate_counterparty(counterparty_id))

    def score(self, counterparty_id: str) -> float:
        """
        Compute counterparty credit domain score D_credit(x) ∈ [0, 1].

        Higher score = lower credit risk = more confidence in the trade.
        """
        profile = self.get_profile(counterparty_id)
        if profile is None:
            return 0.3  # Unknown counterparty → very conservative

        # Collateral coverage ratio
        if profile.exposure_usd > 0:
            coverage = min(1.0, profile.collateral_usd / profile.exposure_usd)
        else:
            coverage = 1.0

        # PD score (invert: low PD = high confidence)
        pd_score = 1.0 - profile.pd_1y

        # Rating score
        rating_pd = _RATING_PD.get(profile.credit_rating, 0.5)
        rating_score = 1.0 - rating_pd

        # Staleness penalty: profiles older than 24h get penalised
        age_hours = (datetime.now(timezone.utc) - profile.last_updated).total_seconds() / 3600
        staleness = _clamp(1.0 - age_hours / 48.0)  # Degrades over 48h

        return _clamp(
            0.30 * pd_score + 0.25 * rating_score
            + 0.25 * coverage + 0.20 * staleness
        )


# ---------------------------------------------------------------------------
# 5. Intraday Position Limiter
# ---------------------------------------------------------------------------

@dataclass
class PositionLimit:
    """Intraday position limit configuration."""
    instrument_id: str
    max_long_lots: float
    max_short_lots: float
    max_notional_usd: float
    warning_pct: float = 0.80  # Warn at 80% of limit


class IntradayPositionLimiter:
    """
    Wires intraday position limits to BUDGET gate thresholds.

    When a proposed trade would push positions beyond limits, the budget gate
    confidence is reduced proportionally.

    Closes gap: *Intraday position limits not yet wired to budget gate thresholds*
    """

    def __init__(self) -> None:
        self._limits: Dict[str, PositionLimit] = {}
        self._positions: Dict[str, float] = {}  # instrument → net lots

    def set_limit(self, limit: PositionLimit) -> None:
        _validate_instrument_id(limit.instrument_id)
        self._limits[limit.instrument_id] = limit

    def update_position(self, instrument_id: str, net_lots: float) -> None:
        _validate_instrument_id(instrument_id)
        self._positions[instrument_id] = net_lots

    def check_trade(
        self, instrument_id: str, side: str, quantity: float, price: float
    ) -> Dict[str, Any]:
        """Check if a proposed trade would breach position limits."""
        inst = _validate_instrument_id(instrument_id)
        if side not in ("BUY", "SELL"):
            raise ValueError("side must be 'BUY' or 'SELL'")
        if quantity <= 0 or price <= 0:
            raise ValueError("quantity and price must be positive")

        current = self._positions.get(inst, 0.0)
        proposed = current + (quantity if side == "BUY" else -quantity)
        notional = abs(proposed * price)

        limit = self._limits.get(inst)
        if limit is None:
            return {"allowed": True, "utilisation": 0.0, "score": 0.7, "message": "No limit configured"}

        # Check directional limits
        long_ok = proposed <= limit.max_long_lots
        short_ok = proposed >= -limit.max_short_lots
        notional_ok = notional <= limit.max_notional_usd

        # Utilisation (worst of the three dimensions)
        if limit.max_long_lots > 0 and proposed > 0:
            long_util = proposed / limit.max_long_lots
        else:
            long_util = 0.0
        if limit.max_short_lots > 0 and proposed < 0:
            short_util = abs(proposed) / limit.max_short_lots
        else:
            short_util = 0.0
        if limit.max_notional_usd > 0:
            notional_util = notional / limit.max_notional_usd
        else:
            notional_util = 0.0

        utilisation = max(long_util, short_util, notional_util)
        allowed = long_ok and short_ok and notional_ok

        # Score: 1.0 at 0% utilisation, 0.0 at 100%+
        score = _clamp(1.0 - utilisation)

        warning = utilisation >= limit.warning_pct and allowed
        msg = "Within limits" if allowed else "POSITION LIMIT BREACH"
        if warning:
            msg = f"WARNING: {utilisation:.0%} of limit reached"

        return {
            "allowed": allowed,
            "utilisation": round(utilisation, 4),
            "score": round(score, 4),
            "warning": warning,
            "message": msg,
        }

    def score(self, instrument_id: str, side: str, quantity: float, price: float) -> float:
        """Compute budget gate score for the proposed trade ∈ [0, 1]."""
        return self.check_trade(instrument_id, side, quantity, price)["score"]


# ---------------------------------------------------------------------------
# 6. Dark Pool Compliance Checker
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DarkPoolRule:
    """Compliance rule for dark pool order routing."""
    rule_id: str
    venue_type: str      # "DARK_POOL" | "LIT" | "SYSTEMATIC_INTERNALISER"
    jurisdiction: str
    max_order_pct: float  # Max % of ADV allowed in dark pool
    pre_trade_waiver: bool
    post_trade_delay_sec: int
    description: str = ""


class DarkPoolComplianceChecker:
    """
    Checks order routing compliance for dark pool venues.

    Verifies that dark pool orders comply with transparency waivers,
    volume caps, and reporting requirements.

    Closes gap: *Dark pool order routing compliance rules pending legal review*
    """

    def __init__(self) -> None:
        self._rules: Dict[str, DarkPoolRule] = {}
        self._load_default_rules()

    def _load_default_rules(self) -> None:
        defaults = [
            DarkPoolRule("DP-SEC-ATS", "DARK_POOL", "US_SEC", 5.0, False, 10, "SEC Reg ATS — volume threshold for dark pools"),
            DarkPoolRule("DP-SEC-NMS", "DARK_POOL", "US_SEC", 8.0, False, 0, "SEC Reg NMS — best execution for dark pool fills"),
            DarkPoolRule("DP-MIFID-DVC", "DARK_POOL", "EU_MIFID2", 4.0, True, 60, "MiFID II Double Volume Cap — 4% venue / 8% EU-wide"),
            DarkPoolRule("DP-MIFID-LIS", "DARK_POOL", "EU_MIFID2", 100.0, True, 120, "MiFID II Large-In-Scale waiver"),
            DarkPoolRule("DP-FCA-SI", "SYSTEMATIC_INTERNALISER", "UK_FCA", 15.0, False, 60, "FCA systematic internaliser reporting obligations"),
        ]
        for rule in defaults:
            self.add_rule(rule)

    def add_rule(self, rule: DarkPoolRule) -> None:
        self._rules[rule.rule_id] = rule

    def check_order(
        self,
        venue_type: str,
        jurisdiction: str,
        order_size_pct_adv: float,
    ) -> List[Dict[str, Any]]:
        """Check dark pool compliance for a proposed order."""
        results: List[Dict[str, Any]] = []
        for rule in self._rules.values():
            if rule.venue_type != venue_type or rule.jurisdiction != jurisdiction:
                continue
            compliant = order_size_pct_adv <= rule.max_order_pct
            results.append({
                "rule_id": rule.rule_id,
                "compliant": compliant,
                "max_pct": rule.max_order_pct,
                "actual_pct": round(order_size_pct_adv, 4),
                "pre_trade_waiver_needed": rule.pre_trade_waiver,
                "post_trade_delay_sec": rule.post_trade_delay_sec,
                "description": rule.description,
            })
        return results

    def score(
        self,
        venue_type: str,
        jurisdiction: str,
        order_size_pct_adv: float,
    ) -> float:
        """
        Compute dark pool compliance score ∈ [0, 1].

        1.0 = fully compliant with all applicable rules.
        """
        checks = self.check_order(venue_type, jurisdiction, order_size_pct_adv)
        if not checks:
            return 0.5  # No rules applicable → conservative

        compliant = sum(1 for c in checks if c["compliant"])
        return _clamp(compliant / len(checks))


# ---------------------------------------------------------------------------
# 7. Unified Financial Domain Engine
# ---------------------------------------------------------------------------

class FinancialDomainEngine:
    """
    Unified financial domain engine that orchestrates all six sub-models
    to produce enriched G(x), D(x), H(x) scores for the MFGC formula.

    Usage::

        engine = FinancialDomainEngine()
        engine.liquidity.update_snapshot(...)
        engine.regulatory.add_rule(...)
        engine.wash_trade.add_trade(...)
        engine.credit.update_profile(...)
        engine.position_limiter.set_limit(...)
        engine.dark_pool.add_rule(...)

        scores = engine.compute_domain_scores(
            instrument_id="AAPL",
            trade_size=1000,
            side="BUY",
            price=150.0,
            account_id="ACC-001",
            counterparty_id="CP-001",
            jurisdictions=["US_SEC"],
            venue_type="DARK_POOL",
            order_pct_adv=2.0,
        )
    """

    def __init__(self) -> None:
        self.liquidity = MarketLiquidityScorer()
        self.regulatory = RegulatoryMapper()
        self.wash_trade = WashTradeDetector()
        self.credit = CounterpartyCreditScorer()
        self.position_limiter = IntradayPositionLimiter()
        self.dark_pool = DarkPoolComplianceChecker()

    def compute_domain_scores(
        self,
        instrument_id: str,
        trade_size: float = 0.0,
        side: str = "BUY",
        price: float = 0.0,
        account_id: str = "",
        counterparty_id: str = "",
        jurisdictions: Optional[List[str]] = None,
        venue_type: str = "LIT",
        order_pct_adv: float = 0.0,
        base_confidence: float = 0.8,
    ) -> Dict[str, float]:
        """
        Compute enriched G(x), D(x), H(x) from all financial sub-models.
        """
        juris = jurisdictions or ["US_SEC"]

        # D(x) components
        d_liquidity = self.liquidity.score(instrument_id, trade_size)
        d_regulatory = self.regulatory.score(juris, base_confidence)
        d_credit = self.credit.score(counterparty_id) if counterparty_id else 0.8
        d_position = (
            self.position_limiter.score(instrument_id, side, trade_size, price)
            if trade_size > 0 and price > 0
            else 0.8
        )
        d_dark_pool = self.dark_pool.score(venue_type, juris[0], order_pct_adv) if venue_type == "DARK_POOL" else 1.0

        # H(x) components
        h_wash = self.wash_trade.score(account_id, instrument_id) if account_id else 0.0

        # Aggregate
        domain = _clamp(
            0.25 * d_liquidity + 0.20 * d_regulatory
            + 0.20 * d_credit + 0.20 * d_position + 0.15 * d_dark_pool
        )
        hazard = h_wash
        goodness = _clamp(0.60 * domain + 0.40 * (1.0 - hazard))

        return {
            "goodness": round(goodness, 4),
            "domain": round(domain, 4),
            "hazard": round(hazard, 4),
            "d_liquidity": round(d_liquidity, 4),
            "d_regulatory": round(d_regulatory, 4),
            "d_credit": round(d_credit, 4),
            "d_position": round(d_position, 4),
            "d_dark_pool": round(d_dark_pool, 4),
            "h_wash": round(h_wash, 4),
        }
