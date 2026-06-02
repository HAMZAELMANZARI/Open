const api = {
    async request(method, url, body) {
        const headers = {"Content-Type": "application/json"};
        const token = localStorage.getItem("token");
        if (token) headers["Authorization"] = `Bearer ${token}`;
        try {
            const res = await fetch(url, {
                method,
                headers,
                body: body ? JSON.stringify(body) : undefined,
            });
            const data = await res.json();
            if (!res.ok) {
                alert(data.error || "Erreur");
                return null;
            }
            return data;
        } catch (e) {
            alert("Erreur réseau");
            return null;
        }
    },
    get(url) { return this.request("GET", url); },
    post(url, body) { return this.request("POST", url, body); },
    put(url, body) { return this.request("PUT", url, body); },
    del(url) { return this.request("DELETE", url); },
};

function showModal(title, bodyHTML) {
    document.getElementById("modal-title").textContent = title;
    document.getElementById("modal-body").innerHTML = bodyHTML;
    document.getElementById("modal-overlay").classList.add("active");
}

function closeModal() {
    document.getElementById("modal-overlay").classList.remove("active");
}


