% SPDX-License-Identifier: AGPL-3.0-only
% Copyright (C) 2026 David contributors
% Executable eligibility rules for Synthetic David sparse router.
% Authoritative symbolic layer: embeddings propose; these rules decide.
% Run: swipl -q -s symbolic_rules.pl -g smoke_cobol -t halt

:- style_check(-singleton).

% ---- risk order ----
risk_rank(low, 0).
risk_rank(medium, 1).
risk_rank(high, 2).
risk_rank(critical, 3).

risk_exceeds(AgentRisk, MaxRisk) :-
    risk_rank(AgentRisk, A),
    risk_rank(MaxRisk, M),
    A > M.

% ---- seed registry (AgentDescriptor facts) ----
agent(legacyCobol).
agent(database).
agent(reverseEngineering).
agent(modernization).
agent(migrationValidation).
agent(provenance).
agent(risk).
agent(audit).
agent(response).
agent(quant).

control_plane(risk).
control_plane(audit).
control_plane(response).

capability(legacyCobol, cobol).
capability(legacyCobol, copybook_analysis).
capability(legacyCobol, control_flow).
capability(legacyCobol, data_flow).
capability(legacyCobol, business_rule_extraction).
capability(legacyCobol, modernization_analysis).
capability(database, schema_analysis).
capability(database, db2).
capability(database, sql).
capability(reverseEngineering, call_graph).
capability(reverseEngineering, control_flow).
capability(reverseEngineering, data_flow).
capability(modernization, cobol_to_java).
capability(modernization, api_mapping).
capability(migrationValidation, equivalence).
capability(migrationValidation, behavioral_compare).
capability(provenance, provenance_dag).
capability(provenance, content_hash).
capability(provenance, authority).
capability(risk, risk_policy).
capability(risk, escalation).
capability(audit, audit_trail).
capability(audit, compliance).
capability(response, synthesis).
capability(response, user_response).
capability(quant, pricing).
capability(quant, monte_carlo).

permission(legacyCobol, read_source).
permission(legacyCobol, read_copybooks).
permission(database, read_schema).
permission(reverseEngineering, read_source).
permission(modernization, read_source).
permission(modernization, write_plan).
permission(migrationValidation, read_outputs).
permission(provenance, read_evidence).
permission(provenance, write_provenance).
permission(risk, read_all_results).
permission(audit, read_all_results).
permission(response, read_conclusions).
permission(quant, read_market_data).

risk_class(legacyCobol, high).
risk_class(database, medium).
risk_class(reverseEngineering, medium).
risk_class(modernization, high).
risk_class(migrationValidation, high).
risk_class(provenance, medium).
risk_class(risk, critical).
risk_class(audit, high).
risk_class(response, medium).
risk_class(quant, medium).

depends(legacyCobol, database).
depends(legacyCobol, reverseEngineering).
depends(legacyCobol, provenance).
depends(modernization, legacyCobol).
depends(modernization, provenance).
depends(migrationValidation, provenance).
depends(migrationValidation, legacyCobol).
depends(audit, provenance).

% ---- request context (dynamic; smoke asserts cobol_req) ----
% required_capability(Req, Cap).
% granted_permission(Req, Perm).
% max_risk_class(Req, Class).

% ---- hard filters ----
capability_eligible(Agent, Req) :-
    control_plane(Agent),
    agent(Agent).
capability_eligible(Agent, Req) :-
    agent(Agent),
    capability(Agent, Cap),
    required_capability(Req, Cap).

permission_eligible(Agent, Req) :-
    agent(Agent),
    forall(permission(Agent, P), granted_permission(Req, P)).

risk_eligible(Agent, Req) :-
    agent(Agent),
    risk_class(Agent, AR),
    max_risk_class(Req, MR),
    \+ risk_exceeds(AR, MR).

% Core eligible: all three hard filters (control-plane still needs risk unless mandatory).
eligible(Agent, Req) :-
    capability_eligible(Agent, Req),
    permission_eligible(Agent, Req),
    risk_eligible(Agent, Req).

% Dependency agents may skip capability intersection; still need permission + risk.
dep_eligible(Agent, Req) :-
    agent(Agent),
    permission_eligible(Agent, Req),
    risk_eligible(Agent, Req).

% Mandatory control plane: permission only (matches scaffold; Risk may be critical).
mandatory_control_eligible(Agent, Req) :-
    control_plane(Agent),
    permission_eligible(Agent, Req).

% ---- dependency closure (BFS via setof/findall) ----
closure(Seed, Closed) :-
    closure_(Seed, [], Closed).

closure_([], Acc, Closed) :-
    reverse(Acc, Closed).
closure_([H|T], Acc, Closed) :-
    memberchk(H, Acc), !,
    closure_(T, Acc, Closed).
closure_([H|T], Acc, Closed) :-
    findall(D, depends(H, D), Deps),
    append(T, Deps, Queue),
    closure_(Queue, [H|Acc], Closed).

% ---- minimum agent set ----
% 1. Collect agents that cover at least one required capability and pass hard filters
% 2. Greedy cover of required capabilities (order by agent atom for determinism)
% 3. Dependency closure; drop incomplete parents if a dep fails dep_eligible
% 4. Append mandatory Risk + Response if permitted

covers_required(Agent, Req, Cap) :-
    required_capability(Req, Cap),
    capability(Agent, Cap).

candidate_core(Agent, Req) :-
    eligible(Agent, Req),
    \+ control_plane(Agent),
    covers_required(Agent, Req, _).

greedy_cover(Req, Selected) :-
    findall(Cap, required_capability(Req, Cap), Caps0),
    sort(Caps0, Caps),
    findall(A, candidate_core(A, Req), Cands0),
    sort(Cands0, Cands),
    greedy_cover_(Caps, Cands, Req, [], Selected).

greedy_cover_([], _, _, Acc, Selected) :-
    reverse(Acc, Selected).
greedy_cover_(Uncovered, Cands, Req, Acc, Selected) :-
    Uncovered \= [],
    best_cover(Uncovered, Cands, Acc, Best, CoverN),
    CoverN > 0, !,
    findall(C, (member(C, Uncovered), \+ capability(Best, C)), Rest),
    greedy_cover_(Rest, Cands, Req, [Best|Acc], Selected).
greedy_cover_(_, _, _, Acc, Selected) :-
    reverse(Acc, Selected).

best_cover(Uncovered, Cands, Already, Best, CoverN) :-
    findall(N-A, (
        member(A, Cands),
        \+ memberchk(A, Already),
        findall(C, (member(C, Uncovered), capability(A, C)), Cs),
        length(Cs, N),
        N > 0
    ), Pairs0),
    sort(0, @>=, Pairs0, Sorted),
    Sorted = [CoverN-Best|_].

filter_closure([], _, []).
filter_closure([A|As], Req, [A|Bs]) :-
    ( memberchk(A, As) -> fail ; true ),
    ( candidate_core(A, Req) -> true
    ; depends_from_selected(A, [A|As]) -> dep_eligible(A, Req)
    ; dep_eligible(A, Req)
    ), !,
    filter_closure(As, Req, Bs).
filter_closure([_|As], Req, Bs) :-
    filter_closure(As, Req, Bs).

% Simpler durable rule: after closure, every member must be dep_eligible;
% seed cores must have been candidate_core.
closed_ok(Closed, Req, Seed) :-
    forall(member(A, Seed), candidate_core(A, Req)),
    forall(member(A, Closed), dep_eligible(A, Req)).

minimum_agent_set(Req, Final) :-
    greedy_cover(Req, Seed),
    closure(Seed, Closed0),
    include(dep_ok(Req), Closed0, Closed),
    % drop any seed whose required deps were filtered out
    include(deps_satisfied(Closed), Closed, CoreKept),
    mandatory_control(Req, Mand),
    append(CoreKept, Mand, Raw),
    list_to_set(Raw, Final).

dep_ok(Req, Agent) :- dep_eligible(Agent, Req).

deps_satisfied(Closed, Agent) :-
    forall(depends(Agent, D), memberchk(D, Closed)).

mandatory_control(Req, Mand) :-
    findall(A, (
        member(A, [risk, response]),
        mandatory_control_eligible(A, Req)
    ), Mand).

% ---- COBOL smoke request ----
assert_cobol_req :-
    retractall(required_capability(cobol_req, _)),
    retractall(granted_permission(cobol_req, _)),
    retractall(max_risk_class(cobol_req, _)),
    assertz(required_capability(cobol_req, cobol)),
    assertz(required_capability(cobol_req, business_rule_extraction)),
    assertz(granted_permission(cobol_req, read_source)),
    assertz(granted_permission(cobol_req, read_copybooks)),
    assertz(granted_permission(cobol_req, read_schema)),
    assertz(granted_permission(cobol_req, read_evidence)),
    assertz(granted_permission(cobol_req, write_provenance)),
    assertz(granted_permission(cobol_req, read_all_results)),
    assertz(granted_permission(cobol_req, read_conclusions)),
    assertz(max_risk_class(cobol_req, high)).

:- dynamic required_capability/2, granted_permission/2, max_risk_class/2.

smoke_cobol :-
    assert_cobol_req,
    minimum_agent_set(cobol_req, Selected),
    format('selected:~w~n', [Selected]),
    ( memberchk(legacyCobol, Selected) -> true ; format('FAIL missing LegacyCobol~n'), halt(1) ),
    ( memberchk(database, Selected) -> true ; format('FAIL missing Database~n'), halt(1) ),
    ( memberchk(provenance, Selected) -> true ; format('FAIL missing Provenance~n'), halt(1) ),
    ( memberchk(quant, Selected) -> format('FAIL Quant present~n'), halt(1) ; true ),
    ( memberchk(risk, Selected) -> true ; format('FAIL missing Risk~n'), halt(1) ),
    ( memberchk(response, Selected) -> true ; format('FAIL missing Response~n'), halt(1) ),
    format('smoke_cobol: OK~n').
