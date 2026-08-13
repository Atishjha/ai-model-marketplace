import { useWallet } from "../hooks/useWallet";

function truncate(address) {
  return address ? `${address.slice(0, 6)}…${address.slice(-4)}` : "";
}

export function WalletConnect({ wallet }) {
  const { address, connecting, error, isCorrectNetwork, connect, disconnect } = wallet;

  if (!address) {
    return (
      <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: "0.4em" }}>
        <button className="btn btn-primary" onClick={connect} disabled={connecting}>
          {connecting ? "Connecting…" : "Connect wallet"}
        </button>
        {error && (
          <span className="mono" style={{ color: "var(--danger)", fontSize: "0.75em" }}>
            {error}
          </span>
        )}
      </div>
    );
  }

  return (
    <div style={{ display: "flex", alignItems: "center", gap: "0.75em" }}>
      {!isCorrectNetwork && (
        <span className="badge" style={{ color: "var(--danger)", borderColor: "rgba(201,106,90,0.4)" }}>
          wrong network
        </span>
      )}
      <span className="hash">{truncate(address)}</span>
      <button className="btn" onClick={disconnect}>
        Disconnect
      </button>
    </div>
  );
}
