const { ethers } = require("hardhat");

async function main() {
  const [deployer] = await ethers.getSigners();
  console.log("Deploying with account:", deployer.address);

  const platformFeeBps = 250; // 2.5% platform fee, adjust as you like

  const Registry = await ethers.getContractFactory("ModelRegistry");
  const registry = await Registry.deploy(platformFeeBps);
  await registry.waitForDeployment();

  const address = await registry.getAddress();
  const deployTx = registry.deploymentTransaction();
  const receipt = await deployTx.wait();

  console.log("ModelRegistry deployed to:", address);
  console.log("Deployed at block:", receipt.blockNumber);
  console.log("");
  console.log("Save into backend/.env:");
  console.log(`  CONTRACT_ADDRESS=${address}`);
  console.log(`  INDEXER_START_BLOCK=${receipt.blockNumber}`);
  console.log("Save into frontend/.env:");
  console.log(`  VITE_CONTRACT_ADDRESS=${address}`);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});