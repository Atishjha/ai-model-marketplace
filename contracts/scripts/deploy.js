const { ethers } = require("hardhat");

async function main() {
  const [deployer] = await ethers.getSigners();
  console.log("Deploying with account:", deployer.address);

  const platformFeeBps = 250; // 2.5% platform fee, adjust as you like

  const Registry = await ethers.getContractFactory("ModelRegistry");
  const registry = await Registry.deploy(platformFeeBps);
  await registry.waitForDeployment();

  const address = await registry.getAddress();
  console.log("ModelRegistry deployed to:", address);
  console.log("Save this address into backend/.env and frontend/.env as CONTRACT_ADDRESS");
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});