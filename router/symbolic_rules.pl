% SPDX-License-Identifier: AGPL-3.0-only
% Copyright (C) 2026 David contributors
% Executable eligibility rules for Synthetic David sparse router.
% Authoritative symbolic layer: embeddings propose; these rules decide.
% Agent facts live in registry_facts.pl (generated from seed_agents.yaml).
% Atom map: registry agent_id → Prolog atom via downcase-first-letter
%   (see agent_id/2 in registry_facts.pl). Quant is a negative agent.
% Run: swipl -q -s symbolic_rules.pl -g smoke_cobol -t halt
% Product path: J writes request + ann_candidate facts, calls run_eligibility/1.

:- style_check(-singleton).
:- include('registry_facts.pl').

% ---- risk order ----
risk_rank(low, 0).
risk_rank(medium, 1).
risk_rank(high, 2).
risk_rank(critical, 3).

risk_exceeds(AgentRisk, MaxRisk) :-
    risk_rank(AgentRisk, A),
    risk_rank(MaxRisk, M),
    A > M.

% ---- request context (dynamic; J / smoke asserts) ----
% required_capability(Req, Cap).
% granted_permission(Req, Perm).
% max_risk_class(Req, Class).
% ann_candidate(Req, AgentAtom).  % optional; when present, core pick restricted

:- dynamic required_capability/2, granted_permission/2, max_risk_class/2.
:- dynamic ann_candidate/2.

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
%    (if ann_candidate/2 facts exist for Req, restrict core seeds to those candidates)
% 2. Greedy cover of required capabilities (order by agent atom for determinism)
% 3. Dependency closure; drop incomplete parents if a dep fails dep_eligible
% 4. Append mandatory Risk + Response if permitted
% Quant has no overlapping caps for COBOL requests → dropped.

covers_required(Agent, Req, Cap) :-
    required_capability(Req, Cap),
    capability(Agent, Cap).

% When ANN candidates are asserted for Req, only those may be core seeds.
% Deps and mandatory control-plane agents are still closed in below.
in_ann_or_unrestricted(Agent, Req) :-
    ( ann_candidate(Req, _) -> ann_candidate(Req, Agent) ; true ).

candidate_core(Agent, Req) :-
    eligible(Agent, Req),
    \+ control_plane(Agent),
    covers_required(Agent, Req, _),
    in_ann_or_unrestricted(Agent, Req).

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

closed_ok(Closed, Req, Seed) :-
    forall(member(A, Seed), candidate_core(A, Req)),
    forall(member(A, Closed), dep_eligible(A, Req)).

minimum_agent_set(Req, Final) :-
    greedy_cover(Req, Seed),
    closure(Seed, Closed0),
    include(dep_ok(Req), Closed0, Closed),
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

% ---- product entry: print selected atoms (J parses this line) ----
run_eligibility(Req) :-
    minimum_agent_set(Req, Selected),
    format('selected:~w~n', [Selected]).

% ---- COBOL smoke request (no ANN candidates → full registry core) ----
assert_cobol_req :-
    retractall(required_capability(cobol_req, _)),
    retractall(granted_permission(cobol_req, _)),
    retractall(max_risk_class(cobol_req, _)),
    retractall(ann_candidate(cobol_req, _)),
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
