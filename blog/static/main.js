const loginBtn = document.getElementById("loginBtn");
const logoutBtn = document.getElementById("logoutBtn");
const publishBtn = document.getElementById("publishBtn");

const authCard = document.getElementById("authCard");
const composerCard = document.getElementById("composerCard");
const authStatus = document.getElementById("authStatus");
const postStatus = document.getElementById("postStatus");
const postsList = document.getElementById("postsList");
const welcomeText = document.getElementById("welcomeText");

const SESSION_KEY = "did_blog_session_token";
const BLOG_APP_ID = "did-blog";

function setStatus(node, text, type = "") {
    node.textContent = text;
    node.className = `status${type ? ` ${type}` : ""}`;
}

function normalizePrivateKey(privateKey) {
    const value = privateKey.trim();
    if (!value) return "";
    return value.startsWith("0x") ? value : `0x${value}`;
}

function getToken() {
    return localStorage.getItem(SESSION_KEY) || "";
}

function setToken(token) {
    localStorage.setItem(SESSION_KEY, token);
}

function clearToken() {
    localStorage.removeItem(SESSION_KEY);
}

async function api(path, options = {}) {
    const token = getToken();
    const headers = {
        "Content-Type": "application/json",
        ...(options.headers || {}),
    };
    if (token) {
        headers.Authorization = `Bearer ${token}`;
    }

    const response = await fetch(path, {
        ...options,
        headers,
    });
    const data = await response.json().catch(() => ({}));
    return { ok: response.ok, status: response.status, data };
}

function formatDate(unixSeconds) {
    return new Date(unixSeconds * 1000).toLocaleString();
}

function renderPosts(posts) {
    if (!posts.length) {
        postsList.innerHTML = "<p class='muted'>No posts yet.</p>";
        return;
    }

    postsList.innerHTML = posts
        .map(
            (post) => `
            <article class="post">
                <h3>${escapeHtml(post.title)}</h3>
                <div class="meta">By ${escapeHtml(post.author_name)} (${escapeHtml(post.did)}) • ${formatDate(post.created_at)}</div>
                <p>${escapeHtml(post.content)}</p>
            </article>
            `
        )
        .join("");
}

function escapeHtml(value) {
    return value
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}

async function loadPosts() {
    const result = await api("/api/posts");
    if (!result.ok) {
        renderPosts([]);
        return;
    }
    renderPosts(result.data.posts || []);
}

async function loadSession() {
    const token = getToken();
    if (!token) {
        authCard.hidden = false;
        composerCard.hidden = true;
        logoutBtn.hidden = true;
        return;
    }

    const me = await api("/api/auth/me");
    if (!me.ok) {
        clearToken();
        authCard.hidden = false;
        composerCard.hidden = true;
        logoutBtn.hidden = true;
        return;
    }

    authCard.hidden = true;
    composerCard.hidden = false;
    logoutBtn.hidden = false;
    welcomeText.textContent = `Welcome, ${me.data.name}`;
}

loginBtn.addEventListener("click", async () => {
    setStatus(authStatus, "Requesting challenge...");

    const did = document.getElementById("didInput").value.trim();
    const privateKey = normalizePrivateKey(document.getElementById("privateKeyInput").value);
    const appId = BLOG_APP_ID;

    if (!did || !privateKey) {
        setStatus(authStatus, "DID and private key are required.", "error");
        return;
    }

    const challenge = await api("/api/auth/request-challenge", {
        method: "POST",
        body: JSON.stringify({ did, appId }),
    });
    if (!challenge.ok) {
        setStatus(authStatus, challenge.data.error || "Challenge request failed.", "error");
        return;
    }

    try {
        setStatus(authStatus, "Signing challenge...");
        const wallet = new ethers.Wallet(privateKey);
        const signature = await wallet.signMessage(challenge.data.message);

        setStatus(authStatus, "Verifying signature...");
        const verify = await api("/api/auth/verify", {
            method: "POST",
            body: JSON.stringify({
                did,
                message: challenge.data.message,
                signature,
                nonce: challenge.data.nonce,
                appId,
            }),
        });

        if (!verify.ok || !verify.data.verified) {
            setStatus(authStatus, verify.data.error || "Verification failed.", "error");
            return;
        }

        setToken(verify.data.token);
        setStatus(authStatus, `Welcome, ${verify.data.name}`, "success");
        await loadSession();
    } catch (error) {
        setStatus(authStatus, `Signing failed: ${error.message}`, "error");
    }
});

logoutBtn.addEventListener("click", async () => {
    await api("/api/auth/logout", { method: "POST" });
    clearToken();
    await loadSession();
    setStatus(authStatus, "You are logged out.");
});

publishBtn.addEventListener("click", async () => {
    const title = document.getElementById("titleInput").value.trim();
    const content = document.getElementById("contentInput").value.trim();

    if (!title || !content) {
        setStatus(postStatus, "Title and content are required.", "error");
        return;
    }

    const result = await api("/api/posts", {
        method: "POST",
        body: JSON.stringify({ title, content }),
    });
    if (!result.ok) {
        setStatus(postStatus, result.data.error || "Failed to publish post.", "error");
        return;
    }

    document.getElementById("titleInput").value = "";
    document.getElementById("contentInput").value = "";
    setStatus(postStatus, "Post published.", "success");
    await loadPosts();
});

async function init() {
    await Promise.all([loadSession(), loadPosts()]);
}

init();
