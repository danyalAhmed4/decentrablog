// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "./DIDRegistry.sol";

/**
 * @title BlogRegistry
 * @dev Manages blog posts where authors must have an active DID
 * Posts are verified by recovering the signer from signature
 */
contract BlogRegistry {
    // Blog post structure
    struct BlogPost {
        bytes32 contentHash;           // keccak256 of title+body
        address author;                // must have active DID in DIDRegistry
        string did;                    // author's DID
        bytes signature;               // ECDSA signature over contentHash
        uint256 publishedAt;          // timestamp of publication
        bool verified;                // whether signature is verified on-chain
    }

    // Reference to DIDRegistry contract
    DIDRegistry public didRegistry;

    // Storage
    BlogPost[] public posts;
    mapping(address => uint256[]) public authorPosts;

    // Events
    event PostPublished(
        uint256 indexed postId,
        address indexed author,
        bytes32 contentHash,
        uint256 timestamp
    );

    event PostVerified(uint256 indexed postId, bool verified);

    /**
     * @dev Constructor
     * @param _didRegistryAddress Address of deployed DIDRegistry contract
     */
    constructor(address _didRegistryAddress) {
        require(_didRegistryAddress != address(0), "INVALID_REGISTRY_ADDRESS");
        didRegistry = DIDRegistry(_didRegistryAddress);
    }

    /**
     * @dev Publish a new blog post
     * Requires the author to have an active DID
     * @param contentHash keccak256 hash of (title + body)
     * @param signature ECDSA signature over contentHash
     * @param authorDID The author's DID string
     */
    function publishPost(
        bytes32 contentHash,
        bytes calldata signature,
        string calldata authorDID
    ) external {
        // Verify author has active DID
        require(
            didRegistry.isDIDActive(msg.sender),
            "AUTHOR_DID_NOT_ACTIVE"
        );

        // Create and store blog post
        BlogPost memory post = BlogPost({
            contentHash: contentHash,
            author: msg.sender,
            did: authorDID,
            signature: signature,
            publishedAt: block.timestamp,
            verified: false
        });

        posts.push(post);
        uint256 postId = posts.length - 1;
        authorPosts[msg.sender].push(postId);

        emit PostPublished(postId, msg.sender, contentHash, block.timestamp);
    }

    /**
     * @dev Verify that a post's signature is valid
     * Recovers signer from (contentHash, signature) using ecrecover
     * @param postId The post ID to verify
     * @return True if signature is valid and matches author
     */
    function verifyPost(uint256 postId) external view returns (bool) {
        require(postId < posts.length, "POST_NOT_FOUND");

        BlogPost storage post = posts[postId];

        // Recover the signer from signature
        address recoveredSigner = _recoverSigner(post.contentHash, post.signature);

        // Verify that recovered signer matches post author
        return recoveredSigner == post.author;
    }

    /**
     * @dev Get a blog post
     * @param postId The post ID
     * @return The BlogPost structure
     */
    function getPost(uint256 postId)
        external
        view
        returns (BlogPost memory)
    {
        require(postId < posts.length, "POST_NOT_FOUND");
        return posts[postId];
    }

    /**
     * @dev Get all post IDs by an author
     * @param author The author's address
     * @return Array of post IDs
     */
    function getAuthorPosts(address author)
        external
        view
        returns (uint256[] memory)
    {
        return authorPosts[author];
    }

    /**
     * @dev Get total post count
     * @return Total number of posts
     */
    function getPostCount() external view returns (uint256) {
        return posts.length;
    }

    /**
     * @dev Internal function to recover signer from signature
     * Uses eth_sign format recovery
     * @param hash The message hash
     * @param signature The signature bytes (r + s + v)
     * @return The recovered signer address
     */
    function _recoverSigner(bytes32 hash, bytes memory signature)
        internal
        pure
        returns (address)
    {
        // Split signature into r, s, v
        require(signature.length == 65, "INVALID_SIGNATURE_LENGTH");

        bytes32 r;
        bytes32 s;
        uint8 v;

        assembly {
            r := mload(add(signature, 32))
            s := mload(add(signature, 64))
            v := byte(0, mload(add(signature, 96)))
        }

        // Adjust v if needed (MetaMask sometimes returns v = 0 or 1)
        if (v < 27) {
            v += 27;
        }

        require(v == 27 || v == 28, "INVALID_SIGNATURE_V");

        // Recover signer
        address signer = ecrecover(hash, v, r, s);
        require(signer != address(0), "INVALID_SIGNATURE");

        return signer;
    }
}
