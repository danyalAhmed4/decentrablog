// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title DIDRegistry
 * @dev Manages Decentralized Identity (DID) documents on-chain
 * Allows users to register, update, and revoke their DID documents
 */
contract DIDRegistry {
    // DID Document structure
    struct DIDDocument {
        string did;                    // "did:eth:0x..."
        address owner;                 // Ethereum address
        string publicKey;              // hex-encoded secp256k1 public key
        string serviceEndpoint;        // e.g. "https://decentrablog.io/did/0x..."
        uint256 createdAt;            // timestamp of registration
        bool active;                   // whether DID is active
    }

    // Mappings for lookups
    mapping(address => DIDDocument) public didDocuments;
    mapping(string => address) public didToAddress;

    // Events
    event DIDRegistered(
        address indexed owner,
        string did,
        uint256 timestamp
    );

    event DIDRevoked(
        address indexed owner,
        string did,
        uint256 timestamp
    );

    event DIDUpdated(
        address indexed owner,
        string did,
        uint256 timestamp
    );

    /**
     * @dev Register a new DID
     * @param did The DID string (should be "did:eth:0x{address}")
     * @param publicKey The secp256k1 public key in hex format
     * @param serviceEndpoint Service endpoint URL for the DID
     */
    function registerDID(
        string calldata did,
        string calldata publicKey,
        string calldata serviceEndpoint
    ) external {
        require(didDocuments[msg.sender].owner == address(0), "DID_ALREADY_REGISTERED");
        require(didToAddress[did] == address(0), "DID_ALREADY_EXISTS");
        require(bytes(publicKey).length > 0, "PUBLIC_KEY_REQUIRED");

        DIDDocument memory doc = DIDDocument({
            did: did,
            owner: msg.sender,
            publicKey: publicKey,
            serviceEndpoint: serviceEndpoint,
            createdAt: block.timestamp,
            active: true
        });

        didDocuments[msg.sender] = doc;
        didToAddress[did] = msg.sender;

        emit DIDRegistered(msg.sender, did, block.timestamp);
    }

    /**
     * @dev Resolve a DID document by address
     * @param owner The Ethereum address owner of the DID
     * @return The DIDDocument
     */
    function resolveDID(address owner)
        external
        view
        returns (DIDDocument memory)
    {
        require(didDocuments[owner].owner != address(0), "DID_NOT_FOUND");
        return didDocuments[owner];
    }

    /**
     * @dev Resolve a DID document by DID string
     * @param did The DID string
     * @return The DIDDocument
     */
    function resolveDIDByString(string calldata did)
        external
        view
        returns (DIDDocument memory)
    {
        address owner = didToAddress[did];
        require(owner != address(0), "DID_NOT_FOUND");
        return didDocuments[owner];
    }

    /**
     * @dev Revoke a DID (set active = false)
     * Only callable by the DID owner
     */
    function revokeDID() external {
        require(didDocuments[msg.sender].owner == msg.sender, "NOT_DID_OWNER");
        require(didDocuments[msg.sender].active, "DID_ALREADY_REVOKED");

        didDocuments[msg.sender].active = false;
        emit DIDRevoked(msg.sender, didDocuments[msg.sender].did, block.timestamp);
    }

    /**
     * @dev Update the service endpoint of a DID
     * Only callable by the DID owner
     * @param newEndpoint The new service endpoint URL
     */
    function updateServiceEndpoint(string calldata newEndpoint) external {
        require(didDocuments[msg.sender].owner == msg.sender, "NOT_DID_OWNER");
        require(didDocuments[msg.sender].active, "DID_NOT_ACTIVE");

        didDocuments[msg.sender].serviceEndpoint = newEndpoint;
        emit DIDUpdated(msg.sender, didDocuments[msg.sender].did, block.timestamp);
    }

    /**
     * @dev Check if a DID is active
     * @param owner The Ethereum address owner of the DID
     * @return True if DID exists and is active
     */
    function isDIDActive(address owner) external view returns (bool) {
        return didDocuments[owner].active;
    }
}
