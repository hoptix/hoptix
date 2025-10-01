#!/usr/bin/env python3
"""
Analytics Service for Hoptix Grading Data

This service provides comprehensive analytics on upselling, upsizing, and add-on performance
from transaction grading data. It analyzes both overall performance and item-specific metrics.
"""

import json
from typing import Dict, List, Any, Optional
from collections import defaultdict, Counter
from datetime import datetime
import logging
from .item_lookup_service import get_item_lookup_service

logger = logging.getLogger(__name__)

from collections import defaultdict, Counter
from typing import Dict, Any, List

class UpsellAnalytics:
    @staticmethod
    def _parse_items_field(value):
        """
        Accepts:
          - "0" or 0  -> []
          - JSON string -> parsed list
          - python list -> as-is
          - any other string (comma/space separated) -> split on commas
        Returns a list[str] of [ItemID_SizeID].
        """
        if value is None or value == 0 or value == "0":
            return []
        if isinstance(value, list):
            return [str(x).strip() for x in value if str(x).strip()]
        if isinstance(value, dict):
            # If someone passed a dict by mistake, flatten values that look like items
            out = []
            for v in value.values():
                if isinstance(v, list):
                    out.extend(v)
                elif isinstance(v, str):
                    out.append(v)
            return [str(x).strip() for x in out if str(x).strip()]
        s = str(value).strip()
        if s.startswith('[') or s.startswith('{'):
            import json
            try:
                parsed = json.loads(s)
                if isinstance(parsed, list):
                    return [str(x).strip() for x in parsed if str(x).strip()]
                return []
            except Exception:
                pass
        # fallback: comma separated
        return [tok.strip() for tok in s.split(',') if tok.strip()]

    @staticmethod
    def calculate_upsell_metrics(transactions: List[Dict], item_lookup=None) -> Dict[str, Any]:
        """
        Updated to use:
          - num_upsell_opportunities, num_upsell_offers, num_upsell_success (declared counts)
          - upsell_candidate_items (candidates)
          - upsell_offered_items (offered)
          - upsell_success_items (converted)
        """
        total_opportunities = 0
        total_offers = 0
        total_successes = 0
        total_revenue = 0.0

        # Item-level tracking across funnel stages
        item_candidate_count = defaultdict(int)
        item_offered_count   = defaultdict(int)
        item_converted_count = defaultdict(int)
        item_revenue         = defaultdict(float)

        # Diagnostics
        violations = {
            "offers_gt_opportunities": 0,
            "successes_gt_offers": 0,
            "declared_vs_list_mismatch": 0
        }

        # Popularity (converted items)
        converted_counter = Counter()

        for tx in transactions:
            # Declared counts
            opportunities = int(tx.get("num_upsell_opportunities", 0) or 0)
            offers = int(tx.get("num_upsell_offers", 0) or 0)
            successes = int(tx.get("num_upsell_success", 0) or 0)

            # Lists
            candidates = UpsellAnalytics._parse_items_field(tx.get("upsell_candidate_items", "0"))
            offered    = UpsellAnalytics._parse_items_field(tx.get("upsell_offered_items", "0"))
            converted  = UpsellAnalytics._parse_items_field(tx.get("upsell_success_items", "0"))

            # Aggregate totals
            total_opportunities += opportunities
            total_offers += offers
            total_successes += successes

            # Sanity checks (diagnostics only; do not mutate inputs)
            if offers > opportunities:
                violations["offers_gt_opportunities"] += 1
            if successes > offers:
                violations["successes_gt_offers"] += 1

            # Check declared vs observed (lengths)
            # We allow that offers can be phrased to multiple items in one utterance,
            # but generally len(offered) should not exceed offers; same for converted/successes.
            observed_mismatch = (
                len(candidates) < opportunities or
                len(offered)    < offers or
                len(converted)  < successes or
                len(converted)  > offers  # cannot convert more than offered
            )
            if observed_mismatch:
                violations["declared_vs_list_mismatch"] += 1

            # Item-level tallies
            for it in candidates:
                item_candidate_count[it] += 1
            for it in offered:
                item_offered_count[it] += 1
            tx_revenue = 0.0
            for it in converted:
                item_converted_count[it] += 1
                converted_counter[it] += 1
                if item_lookup:
                    price = float(item_lookup.get_item_price(it))
                    total_revenue += price
                    tx_revenue += price
                    item_revenue[it] += price
            # (tx_revenue available if you later want per-tx outputs)

        # Unique items across any stage
        all_items = set(item_candidate_count) | set(item_offered_count) | set(item_converted_count)

        # Aggregate rates
        offer_rate = (total_offers / total_opportunities * 100) if total_opportunities > 0 else 0.0
        success_rate = (total_successes / total_offers * 100) if total_offers > 0 else 0.0
        conversion_rate = (total_successes / total_opportunities * 100) if total_opportunities > 0 else 0.0
        avg_rev_per_success = (total_revenue / total_successes) if total_successes > 0 else 0.0

        # By-item metrics
        by_item = {}
        for it in sorted(all_items):
            cand = item_candidate_count[it]
            off  = item_offered_count[it]
            conv = item_converted_count[it]
            by_item[it] = {
                "candidate_count": cand,
                "offered_count": off,
                "converted_count": conv,
                "offer_rate": (off / cand * 100) if cand > 0 else 0.0,
                "conversion_rate": (conv / cand * 100) if cand > 0 else 0.0,
                "success_rate": (conv / off * 100) if off > 0 else 0.0,
                "candidate_coverage": (off / cand * 100) if cand > 0 else 0.0,  # synonym of offer_rate
                "revenue": item_revenue[it],
            }

        return {
            "total_opportunities": total_opportunities,
            "total_offers": total_offers,
            "total_successes": total_successes,
            "offer_rate": offer_rate,
            "success_rate": success_rate,
            "conversion_rate": conversion_rate,
            "total_revenue": total_revenue,
            "avg_revenue_per_success": avg_rev_per_success,
            "violations": violations,
            "by_item": by_item,
            "most_converted_items": dict(converted_counter.most_common(10)),
        }

    @staticmethod
    def calculate_upsell_metrics_by_operator(transactions: List[Dict], item_lookup=None) -> Dict[str, Any]:
        """
        Operator breakdown using the new fields.
        """
        operator_data = defaultdict(lambda: {
            "total_opportunities": 0,
            "total_offers": 0,
            "total_successes": 0,
            "total_revenue": 0.0,
            "item_candidate_count": defaultdict(int),
            "item_offered_count": defaultdict(int),
            "item_converted_count": defaultdict(int),
            "item_revenue": defaultdict(float),
            "converted_counter": Counter(),
            "violations": {
                "offers_gt_opportunities": 0,
                "successes_gt_offers": 0,
                "declared_vs_list_mismatch": 0
            }
        })

        for tx in transactions:
            operator = tx.get("employee_name") or tx.get("employee_id") or "Unknown"

            opp = int(tx.get("num_upsell_opportunities", 0) or 0)
            off = int(tx.get("num_upsell_offers", 0) or 0)
            suc = int(tx.get("num_upsell_success", 0) or 0)

            candidates = UpsellAnalytics._parse_items_field(tx.get("upsell_candidate_items", "0"))
            offered    = UpsellAnalytics._parse_items_field(tx.get("upsell_offered_items", "0"))
            converted  = UpsellAnalytics._parse_items_field(tx.get("upsell_success_items", "0"))

            d = operator_data[operator]
            d["total_opportunities"] += opp
            d["total_offers"] += off
            d["total_successes"] += suc

            if off > opp:
                d["violations"]["offers_gt_opportunities"] += 1
            if suc > off:
                d["violations"]["successes_gt_offers"] += 1
            observed_mismatch = (
                len(candidates) < opp or
                len(offered)    < off or
                len(converted)  < suc or
                len(converted)  > off
            )
            if observed_mismatch:
                d["violations"]["declared_vs_list_mismatch"] += 1

            for it in candidates:
                d["item_candidate_count"][it] += 1
            for it in offered:
                d["item_offered_count"][it] += 1
            for it in converted:
                d["item_converted_count"][it] += 1
                d["converted_counter"][it] += 1
                if item_lookup:
                    price = float(item_lookup.get_item_price(it))
                    d["total_revenue"] += price
                    d["item_revenue"][it] += price

        # finalize
        result = {}
        for op, d in operator_data.items():
            to = d["total_opportunities"]
            tf = d["total_offers"]
            ts = d["total_successes"]
            all_items = set(d["item_candidate_count"]) | set(d["item_offered_count"]) | set(d["item_converted_count"])

            by_item = {}
            for it in sorted(all_items):
                cand = d["item_candidate_count"][it]
                off  = d["item_offered_count"][it]
                conv = d["item_converted_count"][it]
                by_item[it] = {
                    "candidate_count": cand,
                    "offered_count": off,
                    "converted_count": conv,
                    "offer_rate": (off / cand * 100) if cand > 0 else 0.0,
                    "conversion_rate": (conv / cand * 100) if cand > 0 else 0.0,
                    "success_rate": (conv / off * 100) if off > 0 else 0.0,
                    "candidate_coverage": (off / cand * 100) if cand > 0 else 0.0,
                    "revenue": d["item_revenue"][it],
                }

            result[op] = {
                "total_opportunities": to,
                "total_offers": tf,
                "total_successes": ts,
                "offer_rate": (tf / to * 100) if to > 0 else 0.0,
                "success_rate": (ts / tf * 100) if tf > 0 else 0.0,
                "conversion_rate": (ts / to * 100) if to > 0 else 0.0,
                "total_revenue": d["total_revenue"],
                "avg_revenue_per_success": (d["total_revenue"] / ts) if ts > 0 else 0.0,
                "violations": d["violations"],
                "by_item": by_item,
                "most_converted_items": dict(d["converted_counter"].most_common(10))
            }

        return result

class _CommonParse:
    @staticmethod
    def parse_items(value):
        """
        Normalizes an items field to a list[str] of [ItemID_SizeID].
        Accepts "0"/0/None -> [], JSON strings, lists, dicts (flattens lists), or comma-separated strings.
        """
        if value is None or value == 0 or value == "0":
            return []
        if isinstance(value, list):
            return [str(x).strip() for x in value if str(x).strip()]
        if isinstance(value, dict):
            out = []
            for v in value.values():
                if isinstance(v, list):
                    out.extend(v)
                elif isinstance(v, str):
                    out.append(v)
            return [str(x).strip() for x in out if str(x).strip()]
        s = str(value).strip()
        if not s:
            return []
        if s[0] in "[{":
            import json
            try:
                parsed = json.loads(s)
                if isinstance(parsed, list):
                    return [str(x).strip() for x in parsed if str(x).strip()]
            except Exception:
                pass
        return [tok.strip() for tok in s.split(",") if tok.strip()]

class UpsizeAnalytics:
    """
    Metrics for UPSIZE funnel:
      - Candidates: upsize_candidate_items
      - Offered:    upsize_offered_items
      - Converted:  upsize_success_items

    Counts used:
      - num_upsize_opportunities
      - num_upsize_offers
      - num_upsize_success

    Revenue:
      - If item_lookup has get_item_price_delta(item), uses that delta (preferred).
      - Else falls back to get_item_price(item) for converted items.
    """

    # In UpsizeAnalytics.calculate_upsize_metrics(...):
    @staticmethod
    def calculate_upsize_metrics(transactions: List[Dict], item_lookup=None) -> Dict[str, Any]:
        total_opportunities = total_offers = total_successes = 0
        total_revenue = 0.0
        # NEW: track "largest" offers (asking explicitly for the largest size)
        total_largest_offers = 0

        item_candidate_count = defaultdict(int)
        item_offered_count   = defaultdict(int)
        item_converted_count = defaultdict(int)
        item_revenue         = defaultdict(float)

        violations = {"offers_gt_opportunities": 0, "successes_gt_offers": 0, "declared_vs_list_mismatch": 0}
        converted_counter = Counter()

        for tx in transactions:
            opp = int(tx.get("num_upsize_opportunities", 0) or 0)
            off = int(tx.get("num_upsize_offers", 0) or 0)
            suc = int(tx.get("num_upsize_success", 0) or 0)

            # If your grading writes "num_largest_offers" at the transaction level (per prompt #10),
            # roll it into the upsize analytics here:
            total_largest_offers += int(tx.get("num_largest_offers", 0) or 0)

            candidates = _CommonParse.parse_items(tx.get("upsize_candidate_items", "0"))
            offered    = _CommonParse.parse_items(tx.get("upsize_offered_items", "0"))
            converted  = _CommonParse.parse_items(tx.get("upsize_success_items", "0"))

            total_opportunities += opp
            total_offers += off
            total_successes += suc

            if off > opp: violations["offers_gt_opportunities"] += 1
            if suc > off: violations["successes_gt_offers"] += 1
            if (len(candidates) < opp or len(offered) < off or len(converted) < suc or len(converted) > off):
                violations["declared_vs_list_mismatch"] += 1

            for it in candidates: item_candidate_count[it] += 1
            for it in offered:    item_offered_count[it] += 1
            for it in converted:
                item_converted_count[it] += 1
                converted_counter[it] += 1
                if item_lookup:
                    get_delta = getattr(item_lookup, "get_item_price_delta", None)
                    price = float(get_delta(it) if callable(get_delta) else item_lookup.get_item_price(it))
                    total_revenue += price
                    item_revenue[it] += price

        all_items = set(item_candidate_count) | set(item_offered_count) | set(item_converted_count)

        offer_rate = (total_offers / total_opportunities * 100) if total_opportunities > 0 else 0.0
        success_rate = (total_successes / total_offers * 100) if total_offers > 0 else 0.0
        conversion_rate = (total_successes / total_opportunities * 100) if total_opportunities > 0 else 0.0
        avg_rev_per_success = (total_revenue / total_successes) if total_successes > 0 else 0.0
        # NEW:
        largest_offer_rate = (total_largest_offers / total_offers * 100) if total_offers > 0 else 0.0

        by_item = {}
        for it in sorted(all_items):
            cand = item_candidate_count[it]; off = item_offered_count[it]; conv = item_converted_count[it]
            by_item[it] = {
                "candidate_count": cand,
                "offered_count": off,
                "converted_count": conv,
                "offer_rate": (off / cand * 100) if cand > 0 else 0.0,
                "conversion_rate": (conv / cand * 100) if cand > 0 else 0.0,
                "success_rate": (conv / off * 100) if off > 0 else 0.0,
                "candidate_coverage": (off / cand * 100) if cand > 0 else 0.0,
                "revenue": item_revenue[it],
            }

        return {
            "total_opportunities": total_opportunities,
            "total_offers": total_offers,
            "total_successes": total_successes,
            "offer_rate": offer_rate,
            "success_rate": success_rate,
            "conversion_rate": conversion_rate,
            "total_revenue": total_revenue,
            "avg_revenue_per_success": avg_rev_per_success,
            "largest_offers": total_largest_offers,                 # NEW
            "largest_offer_rate": largest_offer_rate,               # NEW
            "violations": violations,
            "by_item": by_item,
            "most_converted_items": dict(converted_counter.most_common(10)),
        }

    @staticmethod
    def calculate_upsize_metrics_by_operator(transactions: List[Dict], item_lookup=None) -> Dict[str, Any]:
        ops = defaultdict(lambda: {
            "total_opportunities": 0,
            "total_offers": 0,
            "total_successes": 0,
            "total_revenue": 0.0,
            "item_candidate_count": defaultdict(int),
            "item_offered_count": defaultdict(int),
            "item_converted_count": defaultdict(int),
            "item_revenue": defaultdict(float),
            "converted_counter": Counter(),
            "violations": {
                "offers_gt_opportunities": 0,
                "successes_gt_offers": 0,
                "declared_vs_list_mismatch": 0
            },
            "total_largest_offers": 0,  # track largest-size offers per operator
        })

        for tx in transactions:
            operator = tx.get("employee_name") or tx.get("employee_id") or "Unknown"
            opp = int(tx.get("num_upsize_opportunities", 0) or 0)
            off = int(tx.get("num_upsize_offers", 0) or 0)
            suc = int(tx.get("num_upsize_success", 0) or 0)
            largest = int(tx.get("num_largest_offers", 0) or 0)

            # ✅ define these before use
            candidates = _CommonParse.parse_items(tx.get("upsize_candidate_items", "0"))
            offered    = _CommonParse.parse_items(tx.get("upsize_offered_items", "0"))
            converted  = _CommonParse.parse_items(tx.get("upsize_success_items", "0"))

            d = ops[operator]
            d["total_opportunities"] += opp
            d["total_offers"] += off
            d["total_successes"] += suc
            d["total_largest_offers"] += largest

            if off > opp:
                d["violations"]["offers_gt_opportunities"] += 1
            if suc > off:
                d["violations"]["successes_gt_offers"] += 1
            if (len(candidates) < opp or len(offered) < off or len(converted) < suc or len(converted) > off):
                d["violations"]["declared_vs_list_mismatch"] += 1

            for it in candidates:
                d["item_candidate_count"][it] += 1
            for it in offered:
                d["item_offered_count"][it] += 1
            for it in converted:
                d["item_converted_count"][it] += 1
                d["converted_counter"][it] += 1
                if item_lookup:
                    get_delta = getattr(item_lookup, "get_item_price_delta", None)
                    price = float(get_delta(it) if callable(get_delta) else item_lookup.get_item_price(it))
                    d["total_revenue"] += price
                    d["item_revenue"][it] += price

        result = {}
        for op, d in ops.items():
            to, tf, ts = d["total_opportunities"], d["total_offers"], d["total_successes"]
            all_items = set(d["item_candidate_count"]) | set(d["item_offered_count"]) | set(d["item_converted_count"])

            by_item = {}
            for it in sorted(all_items):
                cand = d["item_candidate_count"][it]
                off  = d["item_offered_count"][it]
                conv = d["item_converted_count"][it]
                by_item[it] = {
                    "candidate_count": cand,
                    "offered_count": off,
                    "converted_count": conv,
                    "offer_rate": (off / cand * 100) if cand > 0 else 0.0,
                    "conversion_rate": (conv / cand * 100) if cand > 0 else 0.0,
                    "success_rate": (conv / off * 100) if off > 0 else 0.0,
                    "candidate_coverage": (off / cand * 100) if cand > 0 else 0.0,
                    "revenue": d["item_revenue"][it],
                }

            result[op] = {
                "total_opportunities": to,
                "total_offers": tf,
                "total_successes": ts,
                "offer_rate": (tf / to * 100) if to > 0 else 0.0,
                "success_rate": (ts / tf * 100) if tf > 0 else 0.0,
                "conversion_rate": (ts / to * 100) if to > 0 else 0.0,
                "total_revenue": d["total_revenue"],
                "avg_revenue_per_success": (d["total_revenue"] / ts) if ts > 0 else 0.0,
                "largest_offers": d.get("total_largest_offers", 0),
                "largest_offer_rate": (d.get("total_largest_offers", 0) / tf * 100) if tf > 0 else 0.0,
                "violations": d["violations"],
                "by_item": by_item,
                "most_converted_items": dict(d["converted_counter"].most_common(10))
            }
        return result

class AddonAnalytics:
    """
    Metrics for ADD-ON funnel:
      - Candidates: addon_candidate_items
      - Offered:    addon_offered_items
      - Converted:  addon_success_items

    Counts used:
      - num_addon_opportunities
      - num_addon_offers
      - num_addon_success

    Revenue:
      - Uses item_lookup.get_item_price(item) for converted add-ons.
    """

    @staticmethod
    def calculate_addon_metrics(transactions: List[Dict], item_lookup=None) -> Dict[str, Any]:
        total_opportunities = total_offers = total_successes = 0
        total_revenue = 0.0

        item_candidate_count = defaultdict(int)
        item_offered_count   = defaultdict(int)
        item_converted_count = defaultdict(int)
        item_revenue         = defaultdict(float)

        violations = {
            "offers_gt_opportunities": 0,
            "successes_gt_offers": 0,
            "declared_vs_list_mismatch": 0
        }

        converted_counter = Counter()

        for tx in transactions:
            opp = int(tx.get("num_addon_opportunities", 0) or 0)
            off = int(tx.get("num_addon_offers", 0) or 0)
            suc = int(tx.get("num_addon_success", 0) or 0)

            candidates = _CommonParse.parse_items(tx.get("addon_candidate_items", "0"))
            offered    = _CommonParse.parse_items(tx.get("addon_offered_items", "0"))
            converted  = _CommonParse.parse_items(tx.get("addon_success_items", "0"))

            total_opportunities += opp
            total_offers += off
            total_successes += suc

            if off > opp:
                violations["offers_gt_opportunities"] += 1
            if suc > off:
                violations["successes_gt_offers"] += 1
            observed_mismatch = (
                len(candidates) < opp or
                len(offered)    < off or
                len(converted)  < suc or
                len(converted)  > off
            )
            if observed_mismatch:
                violations["declared_vs_list_mismatch"] += 1

            for it in candidates:
                item_candidate_count[it] += 1
            for it in offered:
                item_offered_count[it] += 1
            for it in converted:
                item_converted_count[it] += 1
                converted_counter[it] += 1
                if item_lookup:
                    price = float(item_lookup.get_item_price(it))
                    total_revenue += price
                    item_revenue[it] += price

        all_items = set(item_candidate_count) | set(item_offered_count) | set(item_converted_count)

        offer_rate = (total_offers / total_opportunities * 100) if total_opportunities > 0 else 0.0
        success_rate = (total_successes / total_offers * 100) if total_offers > 0 else 0.0
        conversion_rate = (total_successes / total_opportunities * 100) if total_opportunities > 0 else 0.0
        avg_rev_per_success = (total_revenue / total_successes) if total_successes > 0 else 0.0

        by_item = {}
        for it in sorted(all_items):
            cand = item_candidate_count[it]
            off  = item_offered_count[it]
            conv = item_converted_count[it]
            by_item[it] = {
                "candidate_count": cand,
                "offered_count": off,
                "converted_count": conv,
                "offer_rate": (off / cand * 100) if cand > 0 else 0.0,
                "conversion_rate": (conv / cand * 100) if cand > 0 else 0.0,
                "success_rate": (conv / off * 100) if off > 0 else 0.0,
                "candidate_coverage": (off / cand * 100) if cand > 0 else 0.0,
                "revenue": item_revenue[it],
            }

        return {
            "total_opportunities": total_opportunities,
            "total_offers": total_offers,
            "total_successes": total_successes,
            "offer_rate": offer_rate,
            "success_rate": success_rate,
            "conversion_rate": conversion_rate,
            "total_revenue": total_revenue,
            "avg_revenue_per_success": avg_rev_per_success,
            "violations": violations,
            "by_item": by_item,
            "most_converted_items": dict(converted_counter.most_common(10)),
        }

    @staticmethod
    def calculate_addon_metrics_by_operator(transactions: List[Dict], item_lookup=None) -> Dict[str, Any]:
        ops = defaultdict(lambda: {
            "total_opportunities": 0,
            "total_offers": 0,
            "total_successes": 0,
            "total_revenue": 0.0,
            "item_candidate_count": defaultdict(int),
            "item_offered_count": defaultdict(int),
            "item_converted_count": defaultdict(int),
            "item_revenue": defaultdict(float),
            "converted_counter": Counter(),
            "violations": {
                "offers_gt_opportunities": 0,
                "successes_gt_offers": 0,
                "declared_vs_list_mismatch": 0
            }
        })

        for tx in transactions:
            operator = tx.get("employee_name") or tx.get("employee_id") or "Unknown"
            opp = int(tx.get("num_addon_opportunities", 0) or 0)
            off = int(tx.get("num_addon_offers", 0) or 0)
            suc = int(tx.get("num_addon_success", 0) or 0)

            candidates = _CommonParse.parse_items(tx.get("addon_candidate_items", "0"))
            offered    = _CommonParse.parse_items(tx.get("addon_offered_items", "0"))
            converted  = _CommonParse.parse_items(tx.get("addon_success_items", "0"))

            d = ops[operator]
            d["total_opportunities"] += opp
            d["total_offers"] += off
            d["total_successes"] += suc

            if off > opp:
                d["violations"]["offers_gt_opportunities"] += 1
            if suc > off:
                d["violations"]["successes_gt_offers"] += 1
            if (len(candidates) < opp or len(offered) < off or len(converted) < suc or len(converted) > off):
                d["violations"]["declared_vs_list_mismatch"] += 1

            for it in candidates:
                d["item_candidate_count"][it] += 1
            for it in offered:
                d["item_offered_count"][it] += 1
            for it in converted:
                d["item_converted_count"][it] += 1
                d["converted_counter"][it] += 1
                if item_lookup:
                    price = float(item_lookup.get_item_price(it))
                    d["total_revenue"] += price
                    d["item_revenue"][it] += price

        result = {}
        for op, d in ops.items():
            to, tf, ts = d["total_opportunities"], d["total_offers"], d["total_successes"]
            all_items = set(d["item_candidate_count"]) | set(d["item_offered_count"]) | set(d["item_converted_count"])

            by_item = {}
            for it in sorted(all_items):
                cand = d["item_candidate_count"][it]
                off  = d["item_offered_count"][it]
                conv = d["item_converted_count"][it]
                by_item[it] = {
                    "candidate_count": cand,
                    "offered_count": off,
                    "converted_count": conv,
                    "offer_rate": (off / cand * 100) if cand > 0 else 0.0,
                    "conversion_rate": (conv / cand * 100) if cand > 0 else 0.0,
                    "success_rate": (conv / off * 100) if off > 0 else 0.0,
                    "candidate_coverage": (off / cand * 100) if cand > 0 else 0.0,
                    "revenue": d["item_revenue"][it],
                }

            result[op] = {
                "total_opportunities": to,
                "total_offers": tf,
                "total_successes": ts,
                "offer_rate": (tf / to * 100) if to > 0 else 0.0,
                "success_rate": (ts / tf * 100) if tf > 0 else 0.0,
                "conversion_rate": (ts / to * 100) if to > 0 else 0.0,
                "total_revenue": d["total_revenue"],
                "avg_revenue_per_success": (d["total_revenue"] / ts) if ts > 0 else 0.0,
                "violations": d["violations"],
                "by_item": by_item,
                "most_converted_items": dict(d["converted_counter"].most_common(10))
            }
        return result

class HoptixAnalyticsService:
    """Main analytics service for Hoptix grading data"""
    
    def __init__(self, db=None, location_id=None):
        self.db = db
        self.location_id = location_id
        self.upsell_analytics = UpsellAnalytics()
        self.upsize_analytics = UpsizeAnalytics()
        self.addon_analytics = AddonAnalytics()
        # Create item lookup service with database connection if available
        self.item_lookup = get_item_lookup_service(db, location_id)
    
    def generate_comprehensive_report(self, transactions: List[Dict]) -> Dict[str, Any]:
        """Generate a comprehensive analytics report with structured store -> operator breakdown"""
        logger.info(f"Generating analytics report for {len(transactions)} transactions")
        
        # Get location information
        location_info = self._get_location_info(transactions)
        
        # Calculate store-level metrics
        store_upsell_metrics = self.upsell_analytics.calculate_upsell_metrics(transactions, self.item_lookup)
        store_upsize_metrics = self.upsize_analytics.calculate_upsize_metrics(transactions, self.item_lookup)
        store_addon_metrics = self.addon_analytics.calculate_addon_metrics(transactions, self.item_lookup)
        
        # Calculate operator-level metrics
        upsell_by_operator = self.upsell_analytics.calculate_upsell_metrics_by_operator(transactions, self.item_lookup)
        upsize_by_operator = self.upsize_analytics.calculate_upsize_metrics_by_operator(transactions, self.item_lookup)
        addon_by_operator = self.addon_analytics.calculate_addon_metrics_by_operator(transactions, self.item_lookup)
        
        # Calculate overall performance
        total_transactions = len(transactions)
        complete_transactions = sum(1 for t in transactions if t.get("Complete Transcript?", 0) == 1)
        
        # Calculate average items per transaction
        total_items_initial = sum(t.get("# of Items Ordered", 0) for t in transactions)
        total_items_final = sum(t.get("# of Items Ordered After Upselling, Upsizing, and Add-on Offers", 0) for t in transactions)
        
        # Structure the report in the requested format: Store -> Summary + Items -> Operator -> Items
        report = {
            "store": {
                "location_id": location_info["location_id"],
                "location_name": location_info["location_name"],
                "summary": {
                    "total_transactions": total_transactions,
                    "complete_transactions": complete_transactions,
                    "completion_rate": (complete_transactions / total_transactions * 100) if total_transactions > 0 else 0,
                    "avg_items_initial": total_items_initial / total_transactions if total_transactions > 0 else 0,
                    "avg_items_final": total_items_final / total_transactions if total_transactions > 0 else 0,
                    "avg_item_increase": (total_items_final - total_items_initial) / total_transactions if total_transactions > 0 else 0,
                    "generated_at": datetime.now().isoformat()
                },
                "upselling": {
                    "summary": {
                        "total_opportunities": store_upsell_metrics["total_opportunities"],
                        "total_offers": store_upsell_metrics["total_offers"],
                        "total_successes": store_upsell_metrics["total_successes"],
                        "conversion_rate": store_upsell_metrics["conversion_rate"],
                        "offer_rate": store_upsell_metrics["offer_rate"],
                        "success_rate": store_upsell_metrics["success_rate"],
                        "total_revenue": store_upsell_metrics["total_revenue"]
                    },
                    "item_breakdown": store_upsell_metrics["by_item"]
                },
                "upsizing": {
                    "summary": {
                        "total_opportunities": store_upsize_metrics["total_opportunities"],
                        "total_offers": store_upsize_metrics["total_offers"],
                        "total_successes": store_upsize_metrics["total_successes"],
                        "conversion_rate": store_upsize_metrics["conversion_rate"],
                        "offer_rate": store_upsize_metrics["offer_rate"],
                        "success_rate": store_upsize_metrics["success_rate"],
                        "total_revenue": store_upsize_metrics["total_revenue"],
                        "largest_offers": store_upsize_metrics["largest_offers"],
                        "largest_offer_rate": store_upsize_metrics["largest_offer_rate"]
                    },
                    "item_breakdown": store_upsize_metrics["by_item"]
                },
                "addons": {
                    "summary": {
                        "total_opportunities": store_addon_metrics["total_opportunities"],
                        "total_offers": store_addon_metrics["total_offers"],
                        "total_successes": store_addon_metrics["total_successes"],
                        "conversion_rate": store_addon_metrics["conversion_rate"],
                        "offer_rate": store_addon_metrics["offer_rate"],
                        "success_rate": store_addon_metrics["success_rate"],
                        "total_revenue": store_addon_metrics["total_revenue"]
                    },
                    "item_breakdown": store_addon_metrics["by_item"]
                },
                "operators": self._structure_operator_analytics(upsell_by_operator, upsize_by_operator, addon_by_operator)
            },
            
            # Keep legacy format for backward compatibility
            "summary": {
                "total_transactions": total_transactions,
                "complete_transactions": complete_transactions,
                "completion_rate": (complete_transactions / total_transactions * 100) if total_transactions > 0 else 0,
                "avg_items_initial": total_items_initial / total_transactions if total_transactions > 0 else 0,
                "avg_items_final": total_items_final / total_transactions if total_transactions > 0 else 0,
                "avg_item_increase": (total_items_final - total_items_initial) / total_transactions if total_transactions > 0 else 0,
                "generated_at": datetime.now().isoformat()
            },
            "upselling": store_upsell_metrics,
            "upsizing": store_upsize_metrics,
            "addons": store_addon_metrics,
            "operator_analytics": {
                "upselling": upsell_by_operator,
                "upsizing": upsize_by_operator,
                "addons": addon_by_operator
            },
            "top_performing_items": self._analyze_top_performing_items(transactions),
            "time_analysis": self._analyze_by_time_period(transactions),
            "recommendations": self._generate_recommendations(store_upsell_metrics, store_upsize_metrics, store_addon_metrics)
        }
        
        # Enhance report with actual item names
        enhanced_report = self.item_lookup.enhance_analytics_data(report)
        
        logger.info("Analytics report generated successfully")
        return enhanced_report
    
    def _get_location_info(self, transactions: List[Dict]) -> Dict[str, str]:
        """Extract location information from transactions"""
        location_id = "unknown"
        location_name = "Unknown Location"
        
        if self.location_id:
            location_id = self.location_id
            
        # Try to get location name from database if we have a connection
        if self.db and location_id != "unknown":
            try:
                result = self.db.client.table('locations').select('id, name').eq('id', location_id).execute()
                if result.data:
                    location_name = result.data[0].get('name', 'Unknown Location')
            except Exception as e:
                logger.warning(f"Could not fetch location name: {e}")
                
        return {
            "location_id": location_id,
            "location_name": location_name
        }
    
    def _structure_operator_analytics(self, upsell_by_operator: Dict, upsize_by_operator: Dict, addon_by_operator: Dict) -> Dict[str, Any]:
        """Structure operator analytics in the requested format: Operator -> Summary + Items for each category"""
        structured_operators = {}
        
        # Get all unique operators
        all_operators = set()
        all_operators.update(upsell_by_operator.keys())
        all_operators.update(upsize_by_operator.keys())
        all_operators.update(addon_by_operator.keys())
        
        for operator in all_operators:
            upsell_data = upsell_by_operator.get(operator, {})
            upsize_data = upsize_by_operator.get(operator, {})
            addon_data = addon_by_operator.get(operator, {})
            
            structured_operators[operator] = {
                "upselling": {
                    "summary": {
                        "total_opportunities": upsell_data.get("total_opportunities", 0),
                        "total_offers": upsell_data.get("total_offers", 0),
                        "total_successes": upsell_data.get("total_successes", 0),
                        "conversion_rate": upsell_data.get("conversion_rate", 0),
                        "offer_rate": upsell_data.get("offer_rate", 0),
                        "success_rate": upsell_data.get("success_rate", 0),
                        "total_revenue": upsell_data.get("total_revenue", 0.0)
                    },
                    "item_breakdown": upsell_data.get("by_item", {})
                },
                "upsizing": {
                    "summary": {
                        "total_opportunities": upsize_data.get("total_opportunities", 0),
                        "total_offers": upsize_data.get("total_offers", 0),
                        "total_successes": upsize_data.get("total_successes", 0),
                        "conversion_rate": upsize_data.get("conversion_rate", 0),
                        "offer_rate": upsize_data.get("offer_rate", 0),
                        "success_rate": upsize_data.get("success_rate", 0),
                        "total_revenue": upsize_data.get("total_revenue", 0.0),
                        "largest_offers": upsize_data.get("largest_offers", 0),
                        "largest_offer_rate": upsize_data.get("largest_offer_rate", 0)
                    },
                    "item_breakdown": upsize_data.get("by_item", {})
                },
                "addons": {
                    "summary": {
                        "total_opportunities": addon_data.get("total_opportunities", 0),
                        "total_offers": addon_data.get("total_offers", 0),
                        "total_successes": addon_data.get("total_successes", 0),
                        "conversion_rate": addon_data.get("conversion_rate", 0),
                        "offer_rate": addon_data.get("offer_rate", 0),
                        "success_rate": addon_data.get("success_rate", 0),
                        "total_revenue": addon_data.get("total_revenue", 0.0)
                    },
                    "item_breakdown": addon_data.get("by_item", {})
                }
            }
        
        return structured_operators
    
    def _analyze_top_performing_items(self, transactions: List[Dict]) -> Dict[str, Any]:
        """Analyze top performing items across all categories"""
        item_performance = defaultdict(lambda: {
            "total_opportunities": 0,
            "total_offers": 0,
            "total_successes": 0,
            "upsell_successes": 0,
            "upsize_successes": 0,
            "addon_successes": 0,
            "frequency": 0
        })
        
        for transaction in transactions:
            initial_items = UpsellAnalytics._parse_items_field(transaction.get("Items Initially Requested", "0"))
            
            for item in initial_items:
                stats = item_performance[item]
                stats["frequency"] += 1
                stats["total_opportunities"] += (
                    transaction.get("num_upsell_opportunities", 0) +
                    transaction.get("num_upsize_opportunities", 0) +
                    transaction.get("num_addon_opportunities", 0)
                )
                stats["total_offers"] += (
                    transaction.get("num_upsell_offers", 0) +
                    transaction.get("num_upsize_offers", 0) +
                    transaction.get("num_addon_offers", 0)
                )
                stats["total_successes"] += (
                    transaction.get("num_upsell_success", 0) +
                    transaction.get("num_upsize_success", 0) +
                    transaction.get("num_addon_success", 0)
                )
                stats["upsell_successes"] += transaction.get("num_upsell_success", 0)
                stats["upsize_successes"] += transaction.get("num_upsize_success", 0)
                stats["addon_successes"] += transaction.get("num_addon_success", 0)
        
        # Calculate performance rates and sort
        for item, stats in item_performance.items():
            stats["success_rate"] = (stats["total_successes"] / stats["total_offers"] * 100) if stats["total_offers"] > 0 else 0
            stats["offer_rate"] = (stats["total_offers"] / stats["total_opportunities"] * 100) if stats["total_opportunities"] > 0 else 0
        
        # Sort by different criteria
        by_frequency = sorted(item_performance.items(), key=lambda x: x[1]["frequency"], reverse=True)[:10]
        by_success_rate = sorted(item_performance.items(), key=lambda x: x[1]["success_rate"], reverse=True)[:10]
        by_total_successes = sorted(item_performance.items(), key=lambda x: x[1]["total_successes"], reverse=True)[:10]
        
        return {
            "most_frequent_items": {item: stats for item, stats in by_frequency},
            "highest_success_rate_items": {item: stats for item, stats in by_success_rate},
            "most_successful_items": {item: stats for item, stats in by_total_successes}
        }
    
    def _analyze_by_time_period(self, transactions: List[Dict]) -> Dict[str, Any]:
        """Analyze performance by time periods"""
        time_buckets = defaultdict(lambda: {
            "transactions": 0,
            "upsell_successes": 0,
            "upsize_successes": 0,
            "addon_successes": 0,
            "total_opportunities": 0
        })
        
        for transaction in transactions:
            # Extract date if available
            date_str = transaction.get("Date", "")
            if date_str:
                try:
                    # Parse date and create time bucket (by day)
                    date_obj = datetime.strptime(date_str, "%m/%d/%Y")
                    time_key = date_obj.strftime("%Y-%m-%d")
                    
                    bucket = time_buckets[time_key]
                    bucket["transactions"] += 1
                    bucket["upsell_successes"] += transaction.get("num_upsell_success", 0)
                    bucket["upsize_successes"] += transaction.get("num_upsize_success", 0)
                    bucket["addon_successes"] += transaction.get("num_addon_success", 0)
                    bucket["total_opportunities"] += (
                        transaction.get("num_upsell_opportunities", 0) +
                        transaction.get("num_upsize_opportunities", 0) +
                        transaction.get("num_addon_opportunities", 0)
                    )
                except ValueError:
                    # Skip if date parsing fails
                    continue
        
        # Calculate rates for each time period
        for time_key, bucket in time_buckets.items():
            total_successes = bucket["upsell_successes"] + bucket["upsize_successes"] + bucket["addon_successes"]
            bucket["success_rate"] = (total_successes / bucket["total_opportunities"] * 100) if bucket["total_opportunities"] > 0 else 0
        
        return dict(time_buckets)
    
    def _generate_recommendations(self, upsell_metrics: Dict, upsize_metrics: Dict, addon_metrics: Dict) -> List[str]:
        """Generate actionable recommendations based on analytics"""
        recommendations = []
        
        # Upselling recommendations
        if upsell_metrics["offer_rate"] < 50:
            recommendations.append(f"🎯 Upselling offer rate is only {upsell_metrics['offer_rate']:.1f}%. Train staff to identify and act on more upselling opportunities.")
        
        if upsell_metrics["success_rate"] < 30:
            recommendations.append(f"📈 Upselling success rate is {upsell_metrics['success_rate']:.1f}%. Review upselling scripts and techniques to improve conversion.")
        
        # Upsizing recommendations
        if upsize_metrics["offer_rate"] < 60:
            recommendations.append(f"📏 Upsizing offer rate is {upsize_metrics['offer_rate']:.1f}%. Encourage staff to suggest larger sizes more consistently.")
        
        if upsize_metrics["largest_offer_rate"] < 80:
            recommendations.append(f"⬆️ Only {upsize_metrics['largest_offer_rate']:.1f}% of upsize offers mention the largest option. Train staff to always offer the premium size.")
        
        # Add-on recommendations
        if addon_metrics["offer_rate"] < 40:
            recommendations.append(f"🍟 Add-on offer rate is {addon_metrics['offer_rate']:.1f}%. Focus on suggesting extras like toppings, sides, and premium options.")
        
        # Top item recommendations
        top_map = upsell_metrics.get("most_converted_items")  # <- was most_upsold_items
        if top_map:
            top_upsold = list(top_map.keys())[0]
            recommendations.append(f"⭐ '{top_upsold}' is your top upsold item. Create targeted promotions around this success.")

        if not recommendations:
            recommendations.append("🎉 Great performance across all metrics! Continue current training and focus on consistency.")
        
        return recommendations

    def get_item_specific_report(self, transactions: List[Dict], item_filter: Optional[str] = None) -> Dict[str, Any]:
        """Generate a report focused on specific items"""
        if item_filter:
            # Filter transactions that include the specific item
            filtered_transactions = []
            for transaction in transactions:
                initial_items = UpsellAnalytics._parse_items_field(transaction.get("Items Initially Requested", "0"))
                if any(item_filter.lower() in str(item).lower() for item in initial_items):
                    filtered_transactions.append(transaction)
            transactions = filtered_transactions
        
        return self.generate_comprehensive_report(transactions)
