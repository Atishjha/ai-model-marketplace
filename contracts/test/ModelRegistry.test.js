const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("ModelRegistry", function () {
  let registry, platform, dev, buyer, otherBuyer;
  const FEE_BPS = 250; // 2.5%

  beforeEach(async function () {
    [platform, dev, buyer, otherBuyer] = await ethers.getSigners();
    const Registry = await ethers.getContractFactory("ModelRegistry", platform);
    registry = await Registry.deploy(FEE_BPS);
    await registry.waitForDeployment();
  });

  it("registers a model and stores the first version", async function () {
    const tx = await registry
      .connect(dev)
      .registerModel("SentimentNet", "QmHash1", ethers.parseEther("0.01"), "MIT");
    await expect(tx).to.emit(registry, "ModelRegistered");

    const versions = await registry.getVersions(0);
    expect(versions.length).to.equal(1);
    expect(versions[0].ipfsHash).to.equal("QmHash1");
  });

  it("only the model owner can add a new version", async function () {
    await registry.connect(dev).registerModel("SentimentNet", "QmHash1", 0, "MIT");

    await expect(
      registry.connect(buyer).addVersion(0, "QmHash2", "v2 - retrained")
    ).to.be.revertedWithCustomError(registry, "NotModelOwner");

    await registry.connect(dev).addVersion(0, "QmHash2", "v2 - retrained");
    expect(await registry.getVersionCount(0)).to.equal(2);
  });

  it("splits purchase payment between owner and platform", async function () {
    const price = ethers.parseEther("1.0");
    await registry.connect(dev).registerModel("SentimentNet", "QmHash1", price, "MIT");

    const devBalanceBefore = await ethers.provider.getBalance(dev.address);
    const platformBalanceBefore = await ethers.provider.getBalance(platform.address);

    await registry.connect(buyer).purchaseLicense(0, { value: price });

    const devBalanceAfter = await ethers.provider.getBalance(dev.address);
    const platformBalanceAfter = await ethers.provider.getBalance(platform.address);

    const expectedFee = (price * BigInt(FEE_BPS)) / 10000n;
    const expectedOwnerAmount = price - expectedFee;

    expect(devBalanceAfter - devBalanceBefore).to.equal(expectedOwnerAmount);
    expect(platformBalanceAfter - platformBalanceBefore).to.equal(expectedFee);
    expect(await registry.hasLicense(0, buyer.address)).to.equal(true);
  });

  it("rejects purchase below asking price", async function () {
    const price = ethers.parseEther("1.0");
    await registry.connect(dev).registerModel("SentimentNet", "QmHash1", price, "MIT");

    await expect(
      registry.connect(buyer).purchaseLicense(0, { value: ethers.parseEther("0.5") })
    ).to.be.revertedWithCustomError(registry, "InsufficientPayment");
  });

  it("prevents double purchase by the same buyer", async function () {
    const price = ethers.parseEther("1.0");
    await registry.connect(dev).registerModel("SentimentNet", "QmHash1", price, "MIT");
    await registry.connect(buyer).purchaseLicense(0, { value: price });

    await expect(
      registry.connect(buyer).purchaseLicense(0, { value: price })
    ).to.be.revertedWithCustomError(registry, "AlreadyLicensed");
  });

  it("only lets licensed buyers rate, once each", async function () {
    const price = ethers.parseEther("0.1");
    await registry.connect(dev).registerModel("SentimentNet", "QmHash1", price, "MIT");

    await expect(
      registry.connect(otherBuyer).rateModel(0, 5)
    ).to.be.revertedWithCustomError(registry, "NotLicensed");

    await registry.connect(buyer).purchaseLicense(0, { value: price });
    await registry.connect(buyer).rateModel(0, 4);

    await expect(
      registry.connect(buyer).rateModel(0, 5)
    ).to.be.revertedWithCustomError(registry, "AlreadyRated");

    expect(await registry.getAverageRatingBps(0)).to.equal(40000); // 4.0 stars
  });

  it("rejects out-of-range ratings", async function () {
    const price = 0;
    await registry.connect(dev).registerModel("FreeModel", "QmHash1", price, "MIT");
    await registry.connect(buyer).purchaseLicense(0, { value: 0 });

    await expect(
      registry.connect(buyer).rateModel(0, 6)
    ).to.be.revertedWithCustomError(registry, "InvalidRating");
  });
});