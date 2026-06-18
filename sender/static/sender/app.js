const form = document.getElementById("sender-form");
const startButton = document.getElementById("start-button");
const stopButton = document.getElementById("stop-button");
const statusDot = document.getElementById("status-dot");
const statusText = document.getElementById("status-text");
const messageBar = document.getElementById("message-bar");
const logOutput = document.getElementById("log-output");
const inactiveReport = document.getElementById("inactive-report");
const failedReport = document.getElementById("failed-report");

const counters = {
    processed: document.getElementById("processed-count"),
    sent: document.getElementById("sent-count"),
    inactive: document.getElementById("inactive-count"),
    failed: document.getElementById("failed-count"),
};

let lastCompletedRunId = null;

function csrfToken() {
    return form.querySelector("[name=csrfmiddlewaretoken]").value;
}

function showMessage(text, isError = false) {
    messageBar.textContent = text;
    messageBar.hidden = !text;
    messageBar.classList.toggle("error", isError);
}

function setStatus(text, mode) {
    statusText.textContent = text;
    statusDot.className = `status-dot ${mode || "idle"}`;
}

function setReportLink(element, report) {
    if (report && report.exists && report.url) {
        element.href = report.url;
        element.classList.remove("disabled");
        element.setAttribute("aria-disabled", "false");
        return;
    }

    element.href = "#";
    element.classList.add("disabled");
    element.setAttribute("aria-disabled", "true");
}

function renderStatus(data) {
    counters.processed.textContent = data.stats.processed || 0;
    counters.sent.textContent = data.stats.sent || 0;
    counters.inactive.textContent = data.stats.inactive || 0;
    counters.failed.textContent = data.stats.failed || 0;

    startButton.disabled = data.running;
    stopButton.disabled = !data.running;

    if (data.running) {
        setStatus("Running", "running");
    } else if (data.completed) {
        setStatus("Completed", "idle");
        if (data.run_id && data.run_id !== lastCompletedRunId) {
            lastCompletedRunId = data.run_id;
            if (data.reports.inactive && data.reports.inactive.exists && data.reports.inactive.url) {
                const link = document.createElement("a");
                link.href = data.reports.inactive.url;
                link.download = `whatsapp_inactive_numbers_${data.run_id}.xlsx`;
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
            }
        }
    } else {
        setStatus("Ready", "idle");
    }

    logOutput.textContent = (data.logs || []).join("\n");
    logOutput.scrollTop = logOutput.scrollHeight;

    setReportLink(inactiveReport, data.reports.inactive);
    setReportLink(failedReport, data.reports.failed);
}

async function refreshStatus() {
    const response = await fetch(form.dataset.statusUrl, { cache: "no-store" });
    if (!response.ok) {
        setStatus("Status error", "error");
        return;
    }

    renderStatus(await response.json());
}

form.addEventListener("submit", async (event) => {
    event.preventDefault();
    showMessage("");
    setStatus("Starting", "running");
    startButton.disabled = true;

    try {
        const response = await fetch(form.dataset.startUrl, {
            method: "POST",
            body: new FormData(form),
            headers: {
                "X-CSRFToken": csrfToken(),
            },
        });
        const data = await response.json();

        if (!response.ok || !data.ok) {
            showMessage(data.error || "Process could not start.", true);
            setStatus("Ready", "idle");
        } else {
            showMessage(data.message || "Process started.");
        }
    } catch (error) {
        showMessage(error.message, true);
        setStatus("Status error", "error");
    }

    await refreshStatus();
});

stopButton.addEventListener("click", async () => {
    stopButton.disabled = true;
    showMessage("");

    try {
        const response = await fetch(form.dataset.stopUrl, {
            method: "POST",
            headers: {
                "X-CSRFToken": csrfToken(),
            },
        });
        const data = await response.json();
        showMessage(data.message || "Stop requested.", !data.ok);
    } catch (error) {
        showMessage(error.message, true);
    }

    await refreshStatus();
});

refreshStatus();
window.setInterval(refreshStatus, 1500);
