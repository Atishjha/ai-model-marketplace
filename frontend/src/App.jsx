import { Link, Route, Routes } from "react-router-dom";
import { useWallet } from "./hooks/useWallet";
import { useContract } from "./hooks/useContract";
import { WalletConnect } from "./components/WalletConnect";
import { Marketplace } from "./pages/Marketplace";
import { ModelDetail } from "./pages/ModelDetail";
import { Publish } from "./pages/Publish";

export default function App() {
  const wallet = useWallet();
  const contract = useContract(wallet.provider);

  return (
    <div style={{ minHeight: "100%", display: "flex", flexDirection: "column" }}>
      <header
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          padding: "1.25em 2em",
          borderBottom: "1px solid var(--line)",
        }}
      >
        <Link to="/" style={{ textDecoration: "none", display: "flex", alignItems: "baseline", gap: "0.5em" }}>
          <span style={{ fontFamily: "var(--face-display)", fontSize: "1.3em", fontWeight: 600 }}>Ledger</span>
          <span className="mono" style={{ color: "var(--parchment-dim)", fontSize: "0.75em" }}>model registry</span>
        </Link>

        <nav style={{ display: "flex", alignItems: "center", gap: "1.5em" }}>
          <Link to="/publish" className="btn">
            Publish
          </Link>
          <WalletConnect wallet={wallet} />
        </nav>
      </header>

      <main style={{ flex: 1, padding: "2.5em 2em", maxWidth: "1100px", width: "100%", margin: "0 auto" }}>
        <Routes>
          <Route path="/" element={<Marketplace />} />
          <Route path="/models/:modelId" element={<ModelDetail contract={contract} walletAddress={wallet.address} />} />
          <Route path="/publish" element={<Publish contract={contract} walletAddress={wallet.address} />} />
        </Routes>
      </main>
    </div>
  );
}
