// Example queries for Neo4j Browser (http://localhost:7474) after
// `harness/graph.py serve` or `harness/graph.py load`. See docs/graph.md.

// 1. The whole system: pipeline, agents, their tools and the hybrid routes.
MATCH p = (:Stage)-[:NEXT|RUNS|ON_FAIL]->() RETURN p
UNION
MATCH p = (:Agent)-[r:ROUTED_TO|ESCALATES_TO {backend: 'hybrid'}]->(:Model) RETURN p;

// 2. Design rule: a judge must never have a write tool (agents.py check enforces it).
MATCH (a:Agent {role: 'judge'})-[:CAN_USE]->(t:Tool)
WHERE t.name IN ['Edit', 'Write', 'MultiEdit', 'NotebookEdit']
RETURN a.name AS judge, t.name AS write_tool;

// 3. Best free model per agent, from the evals.
MATCH (a:Agent)-[s:SCORED]->(m:Model {local: true})
WITH a, m, s ORDER BY s.pass_rate DESC, s.seconds
RETURN a.name AS agent, collect(m.label)[0] AS best_local, collect(s.pass_rate)[0] AS pass_rate;

// 4. What each backend costs in risk: the agents routed to a model below 100%.
MATCH (a:Agent)-[r:ROUTED_TO]->(m:Model), (a)-[s:SCORED]->(m)
WHERE s.pass_rate < 1
RETURN r.backend AS backend, a.name AS agent, m.label AS model, s.pass_rate AS pass_rate
ORDER BY backend, agent;

// 5. One run as a chain of calls and checks (latest run).
MATCH (r:Run) WITH r ORDER BY r.updated DESC LIMIT 1
MATCH start = (r)-[:HAS]->(first {seq: 1}), chain = (first)-[:THEN*]->(last)
WHERE NOT (last)-[:THEN]->()
MATCH calls = (:Call {run: r.id})-[:OF|ON]->()
RETURN start, chain, calls;

// 6. Where runs fail: checks that went red, per kind.
MATCH (:Run)-[:HAS]->(c:Check {ok: false})
RETURN c.kind AS check, count(*) AS failures ORDER BY failures DESC;

// 7. Escalations: which local call got stuck and what took over.
MATCH (stuck:Call)-[:THEN*1..2]->(fix:Call {escalated: true})
RETURN stuck.run AS run, stuck.label AS stuck_on, stuck.error AS error,
       fix.label AS escalated_to, fix.seconds AS fixed_in_s;

// 8. Seconds spent per model across every run.
MATCH (c:Call)-[:ON]->(m:Model)
RETURN m.label AS model, m.local AS local, count(c) AS calls, sum(c.seconds) AS seconds
ORDER BY seconds DESC;
