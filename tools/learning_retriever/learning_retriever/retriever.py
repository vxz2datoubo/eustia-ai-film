from __future__ import annotations

import copy
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import yaml


class RetrievalGateError(RuntimeError):
    """Raised when mandatory recall or conflict gates fail closed."""


def _norm(value: Any) -> str:
    text = str(value or "").strip().casefold()
    text = re.sub(r"[\s_/\\-]+", " ", text)
    return " ".join(text.split())


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, set):
        return list(value)
    return [value]


def _norm_set(value: Any) -> set[str]:
    return {_norm(v) for v in _as_list(value) if _norm(v)}


def _feature_bag(task: dict[str, Any]) -> set[str]:
    bag: set[str] = set()
    for key in (
        "dramatic_function",
        "failure_mechanism",
        "relation_type",
        "spatial_action_features",
        "scene_context",
        "character_context",
        "aliases",
        "camera_performance_sound",
        "surface_similarity",
        "negative_features",
    ):
        bag |= _norm_set(task.get(key))
    model = task.get("model") or {}
    if isinstance(model, dict):
        bag |= _norm_set(model.get("aliases"))
        bag |= _norm_set(model.get("family"))
        bag |= _norm_set(model.get("version"))
    return bag


def _fractional_overlap(task_values: Any, case_values: Any) -> float:
    left = _norm_set(task_values)
    right = _norm_set(case_values)
    if not left or not right:
        return 0.0
    return len(left & right) / max(1, min(len(left), len(right)))


def _ref_parts(ref: str) -> tuple[str, str | None]:
    if "#" not in ref:
        return ref, None
    path, anchor = ref.split("#", 1)
    return path, anchor


def _extract_yaml_case_block(path: Path, anchor: str) -> dict[str, Any] | None:
    """Extract only the selected case block from a YAML registry text.

    This deliberately avoids returning the full registry payload to the caller. It
    scans case boundaries in text, then parses only the selected block.
    """
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    start = None
    base_indent = None
    patterns = (
        re.compile(r"^(\s*)-\s+case_id:\s*[\"']?([^\"'#]+)"),
        re.compile(r"^(\s*)case_id:\s*[\"']?([^\"'#]+)"),
    )
    for i, line in enumerate(lines):
        for pat in patterns:
            m = pat.match(line)
            if m and m.group(2).strip() == anchor:
                start = i
                base_indent = len(m.group(1))
                break
        if start is not None:
            break
    if start is None or base_indent is None:
        return None

    end = len(lines)
    for i in range(start + 1, len(lines)):
        line = lines[i]
        if not line.strip():
            continue
        m = re.match(r"^(\s*)-\s+case_id:\s*", line)
        if m and len(m.group(1)) == base_indent:
            end = i
            break
    block = "\n".join(lines[start:end]) + "\n"
    wrapped = "cases:\n" + "\n".join("  " + ln for ln in block.splitlines()) + "\n"
    parsed = yaml.safe_load(wrapped) or {}
    cases = parsed.get("cases") or []
    if cases and isinstance(cases[0], dict):
        return cases[0]
    return None


def _extract_markdown_section(path: Path, anchor: str) -> str | None:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    hit = None
    level = None
    for i, line in enumerate(lines):
        if anchor in line and line.lstrip().startswith("#"):
            hit = i
            level = len(line) - len(line.lstrip("#"))
            break
    if hit is None:
        for i, line in enumerate(lines):
            if anchor in line:
                hit = i
                level = 2
                while hit > 0 and not lines[hit].lstrip().startswith("#"):
                    hit -= 1
                if lines[hit].lstrip().startswith("#"):
                    level = len(lines[hit]) - len(lines[hit].lstrip("#"))
                break
    if hit is None:
        return None
    end = len(lines)
    for i in range(hit + 1, len(lines)):
        line = lines[i]
        if not line.startswith("#"):
            continue
        this_level = len(line) - len(line.lstrip("#"))
        if this_level <= (level or 1):
            end = i
            break
    return "\n".join(lines[hit:end]).strip() + "\n"


@dataclass
class Candidate:
    entry: dict[str, Any]
    score: float
    components: dict[str, float]
    negative_hits: list[str]
    hard: bool = False


class LearningRetriever:
    """Deterministic, authority-aware V1 structured learning retriever."""

    def __init__(
        self,
        project_root: str | Path,
        *,
        index_path: str | Path | None = None,
        index_data: dict[str, Any] | None = None,
        route_data: dict[str, Any] | None = None,
    ) -> None:
        self.project_root = Path(project_root)
        self.index_path = Path(index_path) if index_path else self.project_root / "10_运行时/learning_recall_index.yaml"
        self.index = copy.deepcopy(index_data) if index_data is not None else yaml.safe_load(self.index_path.read_text(encoding="utf-8"))
        route_path = self.project_root / "10_运行时/director_route_index.yaml"
        self.routes = copy.deepcopy(route_data) if route_data is not None else yaml.safe_load(route_path.read_text(encoding="utf-8"))
        self.entries = {e["case_id"]: e for e in self.index.get("entries", [])}
        self.weights = self.index["retrieval_runtime"]["weights"]
        self.default_top_k = int(self.index["retrieval_runtime"].get("top_k_default", 5))

    def _route_map(self) -> dict[str, dict[str, Any]]:
        return {r["id"]: r for r in (self.routes or {}).get("routes", [])}

    def _mandatory_case_ids(self, hard_routes: list[str]) -> tuple[list[str], list[str]]:
        route_map = self._route_map()
        mandatory: list[str] = []
        missing_routes: list[str] = []
        for route_id in hard_routes:
            route = route_map.get(route_id)
            if not route:
                missing_routes.append(route_id)
                continue
            for ref in route.get("mandatory_reads", []) or []:
                path, anchor = _ref_parts(str(ref))
                if anchor and ("学习" in path or "golden" in path.casefold() or "C-DANCE" in path):
                    mandatory.append(anchor)
        return list(dict.fromkeys(mandatory)), missing_routes

    def _negative_hits(self, entry: dict[str, Any], task_bag: set[str]) -> list[str]:
        hits: list[str] = []
        negatives = entry.get("recall_signature", {}).get("negative_retrieval_examples", []) or []
        for neg in negatives:
            required = _norm_set(neg.get("when_all"))
            if required and required.issubset(task_bag):
                hits.append(str(neg.get("id") or "negative"))
        return hits

    def _model_match(self, entry: dict[str, Any], task: dict[str, Any]) -> tuple[str, float]:
        spec = entry.get("recall_signature", {}).get("model_version", {}) or {}
        if not any(spec.get(k) for k in ("families", "versions", "aliases")):
            return "not_bound", 0.0
        model = task.get("model") or {}
        if not isinstance(model, dict):
            model = {}
        tfam = _norm(model.get("family"))
        tver = _norm(model.get("version"))
        talias = _norm_set(model.get("aliases"))
        sfam = _norm_set(spec.get("families"))
        sver = _norm_set(spec.get("versions"))
        salias = _norm_set(spec.get("aliases"))
        family_ok = not sfam or (tfam and tfam in sfam)
        version_ok = not sver or (tver and tver in sver)
        alias_ok = bool(talias & salias) if talias and salias else False
        matched = (family_ok and version_ok and (bool(tfam or tver) or alias_ok)) or alias_ok
        if matched:
            return "match", float(self.weights["model_version"])
        if bool(spec.get("exclusive")):
            return "exclusive_mismatch", 0.0
        return "observed_model_mismatch_nonexclusive", 0.0

    def _scope_filter(self, entry: dict[str, Any], task: dict[str, Any]) -> str | None:
        scope = entry.get("scope", {}) or {}
        classes = set(scope.get("classes") or [])
        current = task.get("scope") or {}
        if not isinstance(current, dict):
            current = {}
        if "EPISODIC_WORK_ITEM" in classes:
            allowed = {_norm(x) for x in scope.get("work_items", []) or []}
            if allowed and _norm(current.get("work_item")) not in allowed:
                return "expired_work_item_scope"
        if "SCENE_LOCAL" in classes:
            allowed = {_norm(x) for x in scope.get("scenes", []) or []}
            if allowed and _norm(current.get("scene")) not in allowed:
                return "expired_scene_local_scope"
        return None

    def _maturity_filter(self, entry: dict[str, Any]) -> str | None:
        m = entry.get("maturity", {}) or {}
        values = {_norm(v) for v in m.values() if v is not None}
        if "deprecated" in values:
            return "deprecated"
        if "needs revalidation" in values:
            return "needs_revalidation"
        if "conflicted" in values:
            return "conflicted"
        return None

    def _conflict_filter(self, entry: dict[str, Any]) -> str | None:
        for conflict in entry.get("conflict_refs", []) or []:
            if isinstance(conflict, str):
                if _norm(conflict).startswith("unresolved"):
                    return "unresolved_conflict"
                continue
            if not isinstance(conflict, dict):
                continue
            if conflict.get("material") and not conflict.get("resolved"):
                return "unresolved_material_conflict"
        return None

    def _score(self, entry: dict[str, Any], task: dict[str, Any], hard: bool) -> Candidate:
        sig = entry.get("recall_signature", {}) or {}
        comps: dict[str, float] = {}
        if hard:
            comps["hard_canonical"] = float(self.weights["hard_canonical"])
        comps["failure_mechanism"] = self.weights["failure_mechanism"] * _fractional_overlap(task.get("failure_mechanism"), sig.get("failure_mechanism"))
        comps["dramatic_function"] = self.weights["dramatic_function"] * _fractional_overlap(task.get("dramatic_function"), sig.get("dramatic_function"))
        relation_overlap = max(
            _fractional_overlap(task.get("relation_type"), sig.get("relation_type")),
            _fractional_overlap(task.get("spatial_action_features"), sig.get("spatial_action_features")),
        )
        comps["spatial_action_relation"] = self.weights["spatial_action_relation"] * relation_overlap
        comps["character_mechanism"] = self.weights["character_mechanism"] * _fractional_overlap(task.get("character_context"), sig.get("character_context"))
        model_state, model_score = self._model_match(entry, task)
        comps["model_version"] = model_score
        comps["camera_performance_sound"] = self.weights["camera_performance_sound"] * _fractional_overlap(task.get("camera_performance_sound"), sig.get("camera_performance_sound"))
        surface_task = _as_list(task.get("surface_similarity")) + _as_list(task.get("aliases"))
        surface_case = _as_list(sig.get("surface_similarity")) + _as_list(sig.get("aliases"))
        comps["surface_similarity"] = self.weights["surface_similarity"] * _fractional_overlap(surface_task, surface_case)
        task_bag = _feature_bag(task)
        neg_hits = self._negative_hits(entry, task_bag)
        if neg_hits and not hard:
            comps["negative_retrieval"] = float(self.weights["negative_retrieval"])
        score = float(sum(comps.values()))
        candidate = Candidate(entry=entry, score=score, components=comps, negative_hits=neg_hits, hard=hard)
        candidate.entry.setdefault("_runtime", {})["model_state"] = model_state
        return candidate

    def retrieve(
        self,
        task: dict[str, Any],
        *,
        top_k: int | None = None,
        expand: bool = False,
        extra_candidate_ids: Iterable[str] | None = None,
        fail_closed: bool = True,
    ) -> dict[str, Any]:
        top_k = int(top_k or self.default_top_k)
        task_id = str(task.get("task_id") or "UNSPECIFIED_TASK")
        hard_routes = list(dict.fromkeys(str(x) for x in _as_list(task.get("hard_routes"))))
        mandatory_ids, missing_routes = self._mandatory_case_ids(hard_routes)
        hard_set = set(mandatory_ids)

        candidate_ids = set(self.entries)
        for cid in extra_candidate_ids or []:
            if cid in self.entries:
                candidate_ids.add(cid)

        scored: list[Candidate] = []
        excluded: list[dict[str, Any]] = []
        unresolved_conflicts: list[dict[str, Any]] = []

        for cid in sorted(candidate_ids):
            entry = copy.deepcopy(self.entries[cid])
            hard = cid in hard_set
            scope_reason = self._scope_filter(entry, task)
            maturity_reason = self._maturity_filter(entry)
            conflict_reason = self._conflict_filter(entry)
            model_state, _ = self._model_match(entry, task)

            if conflict_reason:
                unresolved_conflicts.append({"case_id": cid, "reason": conflict_reason, "material": True})
                if not hard:
                    excluded.append({"case_id": cid, "reason": conflict_reason})
                    continue
            if scope_reason and not hard:
                excluded.append({"case_id": cid, "reason": scope_reason})
                continue
            if maturity_reason in {"deprecated", "needs_revalidation", "conflicted"} and not hard:
                excluded.append({"case_id": cid, "reason": maturity_reason})
                continue
            if model_state == "exclusive_mismatch" and not hard:
                excluded.append({"case_id": cid, "reason": "model_version_mismatch"})
                continue

            cand = self._score(entry, task, hard)
            if cand.negative_hits and not hard and cand.score <= 0:
                excluded.append({"case_id": cid, "reason": "negative_retrieval_example", "negative_hits": cand.negative_hits})
                continue
            if cand.score > 0 or hard:
                scored.append(cand)

        scored.sort(key=lambda c: (-int(c.hard), -c.score, c.entry["case_id"]))
        selected = scored[:top_k]
        selected_ids = {c.entry["case_id"] for c in selected}
        for c in scored:
            if c.hard and c.entry["case_id"] not in selected_ids:
                selected.append(c)
                selected_ids.add(c.entry["case_id"])

        missing_mandatory = [cid for cid in mandatory_ids if cid not in self.entries or cid not in selected_ids]
        mandatory_ok = not missing_routes and not missing_mandatory
        conflict_ok = not unresolved_conflicts

        als = {
            "hard_canonical_invariants": [],
            "live_work_item_locks": [],
            "director_intents": [],
            "causal_mechanisms": [],
            "contextual_policies": [],
            "model_version_lessons": [],
            "known_failure_modes": [],
            "relevant_counterexamples": [],
            "open_hypotheses_and_optional_ab_opportunities": [],
        }
        selected_payloads: dict[str, Any] = {}
        for cand in selected:
            entry = cand.entry
            cid = entry["case_id"]
            maturity = entry.get("maturity", {}) or {}
            transfer_state = _norm(maturity.get("transferable"))
            roles = entry.get("application_roles", []) or []
            if transfer_state == "candidate" or _norm(maturity.get("observation")) == "prompt approved":
                if cid not in als["open_hypotheses_and_optional_ab_opportunities"]:
                    als["open_hypotheses_and_optional_ab_opportunities"].append(cid)
            for role in roles:
                if role in als and role != "open_hypotheses_and_optional_ab_opportunities":
                    als[role].append(cid)
            if expand:
                payload = self.expand_authority_ref(entry["authority_ref"])
                if payload is not None:
                    selected_payloads[cid] = payload

        receipt = {
            "task_id": task_id,
            "index_id": self.index.get("index_id"),
            "index_schema_version": self.index.get("schema_version"),
            "hard_routes": hard_routes,
            "mandatory_case_ids": mandatory_ids,
            "scored_candidates": [
                {
                    "case_id": c.entry["case_id"],
                    "score": round(c.score, 6),
                    "hard": c.hard,
                    "components": {k: round(v, 6) for k, v in c.components.items() if v},
                    "negative_hits": c.negative_hits,
                }
                for c in scored
            ],
            "selected_case_ids": [c.entry["case_id"] for c in selected],
            "selected_authority_refs": [c.entry["authority_ref"] for c in selected],
            "excluded_candidates": excluded,
            "filters_applied": ["scope", "maturity", "model_version", "conflict", "negative_retrieval_examples"],
            "unresolved_conflicts": unresolved_conflicts,
            "mandatory_recall_satisfied": mandatory_ok,
            "top_k": top_k,
            "receipt_complete": False,
        }
        required = self.index.get("receipt_contract", {}).get("required_fields", []) or []
        receipt["receipt_complete"] = all(field in receipt for field in required if field != "receipt_complete")
        receipt["task_fingerprint"] = hashlib.sha256(json.dumps(task, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()[:16]

        status = "PASS" if mandatory_ok and conflict_ok and receipt["receipt_complete"] else "FAIL"
        result = {
            "status": status,
            "applicable_learning_set": als,
            "retrieval_receipt": receipt,
            "expanded_cases": selected_payloads,
        }
        if fail_closed and status != "PASS":
            reasons = []
            if missing_routes:
                reasons.append(f"unknown hard routes: {missing_routes}")
            if missing_mandatory:
                reasons.append(f"mandatory recall missing: {missing_mandatory}")
            if unresolved_conflicts:
                reasons.append("unresolved material learning conflict")
            if not receipt["receipt_complete"]:
                reasons.append("retrieval receipt incomplete")
            raise RetrievalGateError("; ".join(reasons) or "learning retrieval gate failed")
        return result

    def expand_authority_ref(self, ref: str) -> Any:
        path_str, anchor = _ref_parts(ref)
        path = self.project_root / path_str
        if not path.exists():
            return None
        if not anchor:
            return {"authority_ref": ref}
        if path.suffix.casefold() in {".yaml", ".yml"}:
            payload = _extract_yaml_case_block(path, anchor)
            return {"authority_ref": ref, "payload": payload} if payload is not None else None
        if path.suffix.casefold() == ".md":
            section = _extract_markdown_section(path, anchor)
            return {"authority_ref": ref, "payload": section} if section is not None else None
        return None

    def validate_receipt(self, receipt: dict[str, Any]) -> bool:
        required = self.index.get("receipt_contract", {}).get("required_fields", []) or []
        return all(field in receipt for field in required) and bool(receipt.get("mandatory_recall_satisfied")) and bool(receipt.get("receipt_complete"))


def _anchor_exists(path: Path, anchor: str) -> bool:
    if not path.exists():
        return False
    if path.suffix.casefold() in {".yaml", ".yml"}:
        return _extract_yaml_case_block(path, anchor) is not None
    return anchor in path.read_text(encoding="utf-8")


def validate_index(project_root: str | Path) -> list[str]:
    root = Path(project_root)
    index_path = root / "10_运行时/learning_recall_index.yaml"
    route_path = root / "10_运行时/director_route_index.yaml"
    errors: list[str] = []
    if not index_path.exists():
        return ["learning_recall_index.yaml missing"]
    index = yaml.safe_load(index_path.read_text(encoding="utf-8")) or {}
    routes = yaml.safe_load(route_path.read_text(encoding="utf-8")) or {}
    route_ids = {r.get("id") for r in routes.get("routes", [])}
    entry_ids = set()
    for entry in index.get("entries", []) or []:
        cid = entry.get("case_id")
        if not cid:
            errors.append("entry missing case_id")
            continue
        if cid in entry_ids:
            errors.append(f"duplicate case_id: {cid}")
        entry_ids.add(cid)
        ref = entry.get("authority_ref")
        if not ref:
            errors.append(f"{cid}: missing authority_ref")
            continue
        path_str, anchor = _ref_parts(str(ref))
        path = root / path_str
        if not path.exists():
            errors.append(f"{cid}: dangling authority path {path_str}")
        elif anchor and not _anchor_exists(path, anchor):
            errors.append(f"{cid}: dangling authority anchor {anchor}")
        for hard_route in entry.get("hard_routes", []) or []:
            if hard_route not in route_ids:
                errors.append(f"{cid}: unknown hard route {hard_route}")

    for route in routes.get("routes", []) or []:
        for ref in route.get("mandatory_reads", []) or []:
            path_str, anchor = _ref_parts(str(ref))
            if anchor and "学习" in path_str and route.get("id") == "TARGET_ORIENTED_SPATIAL_BINDING":
                if anchor not in entry_ids:
                    errors.append(f"route {route.get('id')}: mandatory case {anchor} absent from recall index")
    embedding = index.get("retrieval_runtime", {}).get("embedding_policy", {}) or {}
    for key in (
        "may_bypass_authority_gate",
        "may_bypass_scope_gate",
        "may_bypass_maturity_gate",
        "may_bypass_model_version_gate",
        "may_bypass_conflict_gate",
        "may_satisfy_mandatory_route_without_canonical_ref",
    ):
        if embedding.get(key) is not False:
            errors.append(f"embedding policy must set {key}=false")
    return errors
