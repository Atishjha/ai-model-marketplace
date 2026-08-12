// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title ModelRegistry
/// @notice Decentralized registry for AI models: ownership, versioning, licensed
///         purchases with automatic payment split, and buyer ratings.
contract ModelRegistry {
    // ── Types ────────────────────────────────────────────────────────────

    struct ModelVersion {
        string ipfsHash;     // CID of this version's model file
        string note;         // e.g. "v1.1 - fixed tokenizer bug"
        uint256 timestamp;
    }

    struct Model {
        address payable owner;  // 20 bytes ─┐ packed into one 32-byte slot
        bool exists;             // 1 byte   ─┘ (was previously its own slot)
        uint256 price;           // in wei
        string name;
        string licenseType;      // e.g. "MIT", "commercial-single-use", "royalty-5pct"
    }

    // ── Storage ──────────────────────────────────────────────────────────

    // immutable: baked into bytecode at deploy time, no SLOAD cost on every read
    address public immutable platformOwner;
    uint256 public immutable platformFeeBps; // basis points, e.g. 250 = 2.5%

    uint256 public nextModelId;
    mapping(uint256 => Model) public models;
    mapping(uint256 => ModelVersion[]) public modelVersions;

    // buyer => hasLicense, per model
    mapping(uint256 => mapping(address => bool)) public hasLicense;

    // ratings: 1-5, one per buyer per model, only after purchase
    mapping(uint256 => mapping(address => uint8)) public ratingOf;
    mapping(uint256 => address[]) private ratersOf;
    mapping(uint256 => uint256) public ratingSum;

    // ── Events ───────────────────────────────────────────────────────────

    event ModelRegistered(uint256 indexed modelId, address indexed owner, string ipfsHash, uint256 price);
    event VersionAdded(uint256 indexed modelId, string ipfsHash, string note, uint256 timestamp);
    event LicensePurchased(uint256 indexed modelId, address indexed buyer, uint256 amountPaid);
    event ModelRated(uint256 indexed modelId, address indexed buyer, uint8 rating);
    event PriceUpdated(uint256 indexed modelId, uint256 newPrice);

    // ── Errors ───────────────────────────────────────────────────────────

    error NotModelOwner();
    error ModelNotFound();
    error AlreadyLicensed();
    error InsufficientPayment();
    error NotLicensed();
    error AlreadyRated();
    error InvalidRating();
    error TransferFailed();

    // ── Modifiers ────────────────────────────────────────────────────────

    modifier onlyModelOwner(uint256 modelId) {
        if (!models[modelId].exists) revert ModelNotFound();
        if (models[modelId].owner != msg.sender) revert NotModelOwner();
        _;
    }

    constructor(uint256 _platformFeeBps) {
        platformOwner = msg.sender;
        platformFeeBps = _platformFeeBps; // e.g. pass 250 for 2.5%
    }

    // ── Core actions ─────────────────────────────────────────────────────

    /// @notice Register a new model. First IPFS hash becomes version 1.
    function registerModel(
        string calldata name,
        string calldata ipfsHash,
        uint256 price,
        string calldata licenseType
    ) external returns (uint256 modelId) {
        modelId = nextModelId;
        unchecked {
            // realistically unreachable overflow (2^256 models) — safe to skip the check
            nextModelId = modelId + 1;
        }

        models[modelId] = Model({
            owner: payable(msg.sender),
            exists: true,
            price: price,
            name: name,
            licenseType: licenseType
        });

        modelVersions[modelId].push(ModelVersion({
            ipfsHash: ipfsHash,
            note: "initial release",
            timestamp: block.timestamp
        }));

        emit ModelRegistered(modelId, msg.sender, ipfsHash, price);
    }

    /// @notice Owner publishes a new version. Old versions stay in history.
    function addVersion(
        uint256 modelId,
        string calldata ipfsHash,
        string calldata note
    ) external onlyModelOwner(modelId) {
        modelVersions[modelId].push(ModelVersion({
            ipfsHash: ipfsHash,
            note: note,
            timestamp: block.timestamp
        }));

        emit VersionAdded(modelId, ipfsHash, note, block.timestamp);
    }

    function updatePrice(uint256 modelId, uint256 newPrice) external onlyModelOwner(modelId) {
        models[modelId].price = newPrice;
        emit PriceUpdated(modelId, newPrice);
    }

    /// @notice Buy a license to the current version. Splits payment:
    ///         platform fee to platformOwner, remainder to model owner.
    ///         Follows checks-effects-interactions to guard against reentrancy.
    function purchaseLicense(uint256 modelId) external payable {
        Model storage m = models[modelId];
        if (!m.exists) revert ModelNotFound();
        if (hasLicense[modelId][msg.sender]) revert AlreadyLicensed();
        if (msg.value < m.price) revert InsufficientPayment();

        // Effects before interactions
        hasLicense[modelId][msg.sender] = true;

        uint256 fee = (msg.value * platformFeeBps) / 10_000;
        uint256 ownerAmount = msg.value - fee;

        emit LicensePurchased(modelId, msg.sender, msg.value);

        // Interactions
        (bool ownerOk, ) = m.owner.call{value: ownerAmount}("");
        if (!ownerOk) revert TransferFailed();

        if (fee > 0) {
            (bool feeOk, ) = payable(platformOwner).call{value: fee}("");
            if (!feeOk) revert TransferFailed();
        }
    }

    /// @notice Rate a model 1-5. Only buyers who hold a license can rate,
    ///         and only once per model.
    function rateModel(uint256 modelId, uint8 rating) external {
        if (!models[modelId].exists) revert ModelNotFound();
        if (!hasLicense[modelId][msg.sender]) revert NotLicensed();
        if (ratingOf[modelId][msg.sender] != 0) revert AlreadyRated();
        if (rating < 1 || rating > 5) revert InvalidRating();

        ratingOf[modelId][msg.sender] = rating;
        ratersOf[modelId].push(msg.sender);
        ratingSum[modelId] += rating;

        emit ModelRated(modelId, msg.sender, rating);
    }

    // ── Views ────────────────────────────────────────────────────────────

    function getVersions(uint256 modelId) external view returns (ModelVersion[] memory) {
        return modelVersions[modelId];
    }

    function getVersionCount(uint256 modelId) external view returns (uint256) {
        return modelVersions[modelId].length;
    }

    function getAverageRatingBps(uint256 modelId) external view returns (uint256) {
        uint256 count = ratersOf[modelId].length;
        if (count == 0) return 0;
        return (ratingSum[modelId] * 10_000) / count; // e.g. 42500 = 4.25 stars
    }

    function getRatingCount(uint256 modelId) external view returns (uint256) {
        return ratersOf[modelId].length;
    }
}
