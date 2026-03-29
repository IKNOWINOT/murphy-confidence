# Copyright © 2020-2026 Inoni Limited Liability Company. All rights reserved.
# Created by: Corey Post

"""
murphy_confidence.domain
========================
Vertical-specific domain sub-models that compute specialised G(x), D(x),
and H(x) scores for the MFGC confidence engine.

Sub-modules
-----------
healthcare     — Clinical decision support (drug interactions, allergy
                 cross-reference, FHIR adapter, longitudinal history,
                 paediatric dosing)
financial      — Trading compliance (market liquidity, regulatory mapping,
                 wash-trade detection, counterparty credit, intraday limits,
                 dark-pool compliance)
manufacturing  — Factory IoT safety (OPC-UA adapter, multi-sensor fusion,
                 predictive maintenance, SIL-2 mapping, human-presence
                 detection, dynamic hazard recalibration)
cross_system   — Cross-cutting infrastructure (integration runner, perf
                 benchmarks, adversarial robustness, multi-tenant isolation,
                 GateCompiler load testing)

Zero external dependencies.
"""

from .healthcare import (
    DrugInteractionScorer,
    AllergyCrossReference,
    FHIRAdapter,
    LongitudinalHistoryScorer,
    PaediatricDosingModel,
    HealthcareDomainEngine,
)
from .financial import (
    MarketLiquidityScorer,
    RegulatoryMapper,
    WashTradeDetector,
    CounterpartyCreditScorer,
    IntradayPositionLimiter,
    DarkPoolComplianceChecker,
    FinancialDomainEngine,
)
from .manufacturing import (
    OPCUAStreamAdapter,
    MultiSensorFusion,
    PredictiveMaintenanceModel,
    SIL2CertificationMapper,
    HumanPresenceDetector,
    DynamicHazardRecalibrator,
    ManufacturingDomainEngine,
)

__all__ = [
    # Healthcare
    "DrugInteractionScorer",
    "AllergyCrossReference",
    "FHIRAdapter",
    "LongitudinalHistoryScorer",
    "PaediatricDosingModel",
    "HealthcareDomainEngine",
    # Financial
    "MarketLiquidityScorer",
    "RegulatoryMapper",
    "WashTradeDetector",
    "CounterpartyCreditScorer",
    "IntradayPositionLimiter",
    "DarkPoolComplianceChecker",
    "FinancialDomainEngine",
    # Manufacturing
    "OPCUAStreamAdapter",
    "MultiSensorFusion",
    "PredictiveMaintenanceModel",
    "SIL2CertificationMapper",
    "HumanPresenceDetector",
    "DynamicHazardRecalibrator",
    "ManufacturingDomainEngine",
]
