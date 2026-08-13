# ai-model-marketplace
Blockchain Side Project
# AI Model Marketplace

A decentralized marketplace for publishing, licensing, and rating AI models — ownership and payments are enforced on-chain, model files live on IPFS, and a Postgres-backed indexer mirrors on-chain activity for fast browsing.

```
Developer publishes a model
        │
        ▼
File uploads directly to IPFS (browser → Pinata, backend never touches the bytes)
        │
        ▼
registerModel() on-chain — ownership + IPFS hash recorded on Polygon
        │
        ▼
Indexer mirrors the event into Postgres
        │
        ▼
Buyer browses the marketplace, purchases a license via smart contract
        │
        ▼
Payment splits automatically: platform fee + model owner, on-chain
```

## Features

- **Model registration** — publish a model with a name, license type, and price; ownership is recorded on-chain, not in a database that could be edited
- **Ownership verification** — the contract, not a server, is the source of truth for who owns what
- **Version history** — every re-upload is appended on-chain, nothing is ever overwritten
- **Smart-contract payments** — `purchaseLicense()` splits payment between the model owner and the platform automatically, no manual payout step
- **Rating system** — only verified buyers (an on-chain license check) can rate a model, once each
- **Marketplace browsing** — search, filter by license type and rating, all served from an indexed Postgres mirror so browsing never waits on the chain
- **License / IP tracking** — license type is part of the on-chain record, immutable per model

## Architecture

| Layer | Stack |
|---|---|
| Smart contract | Solidity, Hardhat, deployed to Polygon Amoy (testnet) |
| Storage | IPFS via Pinata — direct browser-to-IPFS upload using short-lived signed URLs |
| Backend | FastAPI, SQLAlchemy (async), Postgres, web3.py |
| Indexer | Polling background task mirroring on-chain events into Postgres |
| Frontend | React (Vite), ethers.js, MetaMask |

A deliberate design choice worth calling out: **the backend never touches model files.** The frontend requests a short-lived signed URL from the backend, then uploads directly to Pinata — the backend's only job is minting that URL and never proxies the actual bytes. This keeps large model files off a single server entirely.

Similarly, the frontend never queries the chain for marketplace listings — those are served from Postgres, kept in sync by a background indexer that polls for `ModelRegistered`, `VersionAdded`, `LicensePurchased`, `ModelRated`, and `PriceUpdated` events. On-chain calls only happen for the things that must be on-chain: registering, purchasing, and rating.

## Project structure

```
ai-model-marketplace/
├── contracts/      # Solidity contract, Hardhat config, deploy script, tests
├── backend/        # FastAPI app: upload, marketplace API, indexer
└── frontend/       # React app: marketplace, model detail, publish flow
```

## Running locally

Three services, three terminals.

**1. Deploy the contract** (one-time)
```bash
cd contracts
cp .env.example .env   # fill in AMOY_RPC_URL and PRIVATE_KEY
npm install
npx hardhat test       # confirm all tests pass first
npm run deploy:amoy    # prints CONTRACT_ADDRESS and INDEXER_START_BLOCK
cp artifacts/contracts/ModelRegistry.sol/ModelRegistry.json ../backend/contracts_abi/ModelRegistry.json
```

**2. Start Postgres and the backend**
```bash
docker run --name marketplace-db -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=marketplace -p 5432:5432 -v marketplace-db-data:/var/lib/postgresql/data -d postgres:16

cd backend
cp .env.example .env   # fill in DATABASE_URL, WEB3_PROVIDER_URL, CONTRACT_ADDRESS, INDEXER_START_BLOCK, PINATA_JWT
pip install -r requirements.txt
uvicorn app.main:app --reload
```
Confirm with `curl http://localhost:8000/health` → `{"status": "ok"}`.

**3. Start the frontend**
```bash
cd frontend
cp .env.example .env   # fill in VITE_CONTRACT_ADDRESS
npm install
npm run dev
```

Connect a wallet on Polygon Amoy, publish a model, and it'll appear in the marketplace once the indexer's next poll cycle picks it up (a few seconds).

### Getting testnet credentials

- **RPC URL** — free from [Alchemy](https://alchemy.com) or [Infura](https://infura.io); select **Polygon Amoy** specifically, not mainnet
- **Testnet MATIC** — [faucet.polygon.technology](https://faucet.polygon.technology), select Amoy
- **Pinata JWT** — free at [pinata.cloud](https://pinata.cloud) → API Keys → New Key

### Common local setup issues

- **`WEB3_PROVIDER_URL` / `CONTRACT_ADDRESS` field required** — these have no default; the backend won't start without them in `.env`
- **`chain id 80002` but connected to `137`** — your RPC URL is pointed at Polygon mainnet, not Amoy; double-check which network the RPC app was created for
- **`InvalidPasswordError` against Postgres despite the right password in `.env`** — check for a port conflict first (`netstat -ano | findstr :5432` on Windows) before assuming it's a config issue; a pre-existing Postgres install or another container can silently intercept the port
- **A hand-edited `.env` with duplicate variable lines** — dotenv uses whichever line it parses first; if you've edited a value more than once, check the whole file for a stray earlier line still in effect

## Deployment

Free-tier stack: **Vercel** (frontend) + **Render** (backend) + **Neon** (Postgres — used instead of Render's own free Postgres, which expires 30 days after creation).

One tradeoff worth knowing: Render's free web service spins down after 15 minutes of inactivity. The first request after idle time takes 30–60 seconds to wake up, and the indexer isn't polling while asleep — it catches up automatically once a request wakes the service.

## Known limitations

- Deployed to Polygon **Amoy testnet**, not mainnet — this is a portfolio/demo project, not handling real funds
- The indexer assumes no chain reorgs deeper than `INDEXER_CONFIRMATIONS` blocks; deep reorgs would require manual reconciliation
- No admin/moderation layer — anyone can register a model with any name

## License

MIT