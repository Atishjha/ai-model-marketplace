import { useState } from "react";

export function RatingWidget({ contract, modelId, hasLicense, onRated }) {
  const [selected, setSelected] = useState(0);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  const submit = async (value) => {
    if (!contract) return;
    setSubmitting(true);
    setError(null);
    try {
      const tx = await contract.rateModel(modelId, value);
      await tx.wait();
      setSelected(value);
      onRated?.(value);
    } catch (err) {
      setError(err?.reason || err?.message || "Rating failed");
    } finally {
      setSubmitting(false);
    }
  };

  if (!hasLicense) {
    return (
      <span className="mono" style={{ color: "var(--parchment-dim)", fontSize: "0.85em" }}>
        buy a license to rate this model
      </span>
    );
  }

  return (
    <div>
      <div style={{ display: "flex", gap: "0.3em" }}>
        {[1, 2, 3, 4, 5].map((n) => (
          <button
            key={n}
            className="btn"
            disabled={submitting}
            onClick={() => submit(n)}
            style={{
              padding: "0.4em 0.7em",
              borderColor: n <= selected ? "var(--copper)" : "var(--line)",
              color: n <= selected ? "var(--copper-bright)" : "var(--parchment)",
            }}
          >
            {n}
          </button>
        ))}
      </div>
      {error && (
        <p className="mono" style={{ color: "var(--danger)", fontSize: "0.8em", marginTop: "0.5em" }}>
          {error}
        </p>
      )}
    </div>
  );
}
