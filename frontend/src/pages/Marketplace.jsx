import { useEffect, useState } from "react";
import { fetchModels } from "../lib/api";
import { ModelCard } from "../components/ModelCard";

export function Marketplace() {
  const [models, setModels] = useState([]);
  const [total, setTotal] = useState(0);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    const timeout = setTimeout(() => {
      fetchModels({ search, sort: "newest" })
        .then((data) => {
          if (cancelled) return;
          setModels(data.items);
          setTotal(data.total);
        })
        .catch((err) => !cancelled && setError(err.message))
        .finally(() => !cancelled && setLoading(false));
    }, 250); // debounce search input

    return () => {
      cancelled = true;
      clearTimeout(timeout);
    };
  }, [search]);

  return (
    <div>
      <div style={{ marginBottom: "2em" }}>
        <h1 style={{ fontSize: "2em", marginBottom: "0.3em" }}>The ledger</h1>
        <p style={{ color: "var(--parchment-dim)" }}>
          Every model here traces back to an on-chain registration — ownership isn't a claim, it's a lookup.
          {total > 0 && ` ${total} registered so far.`}
        </p>
      </div>

      <input
        type="text"
        placeholder="Search models…"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        style={{
          width: "100%",
          padding: "0.75em 1em",
          marginBottom: "1.5em",
          background: "var(--ink-800)",
          border: "1px solid var(--line)",
          borderRadius: "3px",
          color: "var(--parchment)",
          fontFamily: "var(--face-mono)",
          fontSize: "0.9em",
        }}
      />

      {loading && <p className="mono" style={{ color: "var(--parchment-dim)" }}>loading…</p>}
      {error && <p style={{ color: "var(--danger)" }}>{error}</p>}
      {!loading && !error && models.length === 0 && (
        <p className="mono" style={{ color: "var(--parchment-dim)" }}>no models match — try a different search.</p>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))", gap: "1em" }}>
        {models.map((model) => (
          <ModelCard key={model.id} model={model} />
        ))}
      </div>
    </div>
  );
}
