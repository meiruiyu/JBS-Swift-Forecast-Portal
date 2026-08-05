// =========================================================
// Shared authentication helper
// =========================================================

async function readJsonResponse(response) {
    let data = {};

    try {
        data = await response.json();
    } catch (error) {
        data = {};
    }

    if (!response.ok) {
        const requestError = new Error(
            data.error ||
            "The request could not be completed."
        );

        requestError.status = response.status;
        requestError.data = data;

        throw requestError;
    }

    return data;
}


// =========================================================
// Registration page
// =========================================================

const registerForm =
    document.getElementById("register-form");

if (registerForm) {
    registerForm.addEventListener(
        "submit",
        async function (event) {
            event.preventDefault();

            const firstName =
                document
                    .getElementById("first-name")
                    .value
                    .trim();

            const lastName =
                document
                    .getElementById("last-name")
                    .value
                    .trim();

            const email =
                document
                    .getElementById("register-email")
                    .value
                    .trim()
                    .toLowerCase();

            const password =
                document
                    .getElementById("register-password")
                    .value;

            const confirmPassword =
                document
                    .getElementById("confirm-password")
                    .value;

            const terms =
                document.getElementById("terms");

            const firstNameError =
                document.getElementById(
                    "first-name-error"
                );

            const lastNameError =
                document.getElementById(
                    "last-name-error"
                );

            const emailError =
                document.getElementById(
                    "email-error"
                );

            const passwordError =
                document.getElementById(
                    "password-error"
                );

            const confirmPasswordError =
                document.getElementById(
                    "confirm-password-error"
                );

            const termsError =
                document.getElementById(
                    "terms-error"
                );

            const submitButton =
                registerForm.querySelector(
                    'button[type="submit"]'
                );

            let isValid = true;

            firstNameError.textContent = "";
            lastNameError.textContent = "";
            emailError.textContent = "";
            passwordError.textContent = "";
            confirmPasswordError.textContent = "";
            termsError.textContent = "";

            if (firstName === "") {
                firstNameError.textContent =
                    "First name is required.";

                isValid = false;
            }

            if (lastName === "") {
                lastNameError.textContent =
                    "Last name is required.";

                isValid = false;
            }

            if (email === "") {
                emailError.textContent =
                    "Columbia email is required.";

                isValid = false;
            } else if (
                !/^[A-Za-z0-9._%+\-]+@columbia\.edu$/i
                    .test(email)
            ) {
                emailError.textContent =
                    "Please enter a valid @columbia.edu email address.";

                isValid = false;
            }

            if (password === "") {
                passwordError.textContent =
                    "Password is required.";

                isValid = false;
            } else if (password.length < 8) {
                passwordError.textContent =
                    "Password must contain at least 8 characters.";

                isValid = false;
            } else if (
                !/[A-Z]/.test(password) ||
                !/[a-z]/.test(password) ||
                !/[0-9]/.test(password)
            ) {
                passwordError.textContent =
                    "Password must include uppercase, lowercase, and a number.";

                isValid = false;
            }

            if (confirmPassword === "") {
                confirmPasswordError.textContent =
                    "Please confirm your password.";

                isValid = false;
            } else if (
                password !== confirmPassword
            ) {
                confirmPasswordError.textContent =
                    "Passwords do not match.";

                isValid = false;
            }

            if (!terms.checked) {
                termsError.textContent =
                    "You must agree to the Terms of Use and Privacy Policy.";

                isValid = false;
            }

            if (!isValid) {
                return;
            }

            submitButton.disabled = true;
            submitButton.textContent =
                "Sending Code...";

            try {
                const response = await fetch(
                    "/api/register",
                    {
                        method: "POST",

                        headers: {
                            "Content-Type":
                                "application/json"
                        },

                        body: JSON.stringify({
                            firstName: firstName,
                            lastName: lastName,
                            email: email,
                            password: password
                        })
                    }
                );

                await readJsonResponse(response);

                window.location.href = "/verify";

            } catch (error) {
                console.error(error);

                emailError.textContent =
                    error.message ||
                    "Unable to create the account.";

            } finally {
                submitButton.disabled = false;
                submitButton.textContent =
                    "Create Account";
            }
        }
    );
}


// =========================================================
// Verification page
// =========================================================

const verifyForm =
    document.getElementById("verify-form");

if (verifyForm) {
    verifyForm.addEventListener(
        "submit",
        async function (event) {
            event.preventDefault();

            const verificationCode =
                document
                    .getElementById(
                        "verification-code"
                    )
                    .value
                    .trim();

            const verificationCodeError =
                document.getElementById(
                    "verification-code-error"
                );

            const submitButton =
                verifyForm.querySelector(
                    'button[type="submit"]'
                );

            verificationCodeError.textContent = "";

            if (verificationCode === "") {
                verificationCodeError.textContent =
                    "Verification code is required.";

                return;
            }

            if (
                !/^\d{6}$/.test(
                    verificationCode
                )
            ) {
                verificationCodeError.textContent =
                    "Please enter a valid 6-digit verification code.";

                return;
            }

            submitButton.disabled = true;
            submitButton.textContent =
                "Verifying...";

            try {
                const response = await fetch(
                    "/api/verify",
                    {
                        method: "POST",

                        headers: {
                            "Content-Type":
                                "application/json"
                        },

                        body: JSON.stringify({
                            code: verificationCode
                        })
                    }
                );

                await readJsonResponse(response);

                window.location.href = "/login";

            } catch (error) {
                console.error(error);

                verificationCodeError.textContent =
                    error.message ||
                    "Unable to verify the code.";

            } finally {
                submitButton.disabled = false;
                submitButton.textContent =
                    "Verify Account";
            }
        }
    );
}


// =========================================================
// Resend verification code
// =========================================================

const resendCodeButton =
    document.getElementById(
        "resend-code-button"
    );

if (resendCodeButton) {
    resendCodeButton.addEventListener(
        "click",
        async function (event) {
            event.preventDefault();

            const verificationCodeError =
                document.getElementById(
                    "verification-code-error"
                );

            verificationCodeError.textContent = "";

            resendCodeButton.disabled = true;
            resendCodeButton.textContent =
                "Sending...";

            try {
                const response = await fetch(
                    "/api/resend-code",
                    {
                        method: "POST"
                    }
                );

                const data =
                    await readJsonResponse(response);

                verificationCodeError.textContent =
                    data.message ||
                    "A new verification code was sent.";

            } catch (error) {
                console.error(error);

                verificationCodeError.textContent =
                    error.message ||
                    "Unable to resend the code.";

            } finally {
                resendCodeButton.disabled = false;
                resendCodeButton.textContent =
                    "Resend Code";
            }
        }
    );
}


// =========================================================
// Login page
// =========================================================

const loginForm =
    document.getElementById("login-form");

if (loginForm) {
    loginForm.addEventListener(
        "submit",
        async function (event) {
            event.preventDefault();

            const email =
                document
                    .getElementById("login-email")
                    .value
                    .trim()
                    .toLowerCase();

            const password =
                document
                    .getElementById(
                        "login-password"
                    )
                    .value;

            const emailError =
                document.getElementById(
                    "login-email-error"
                );

            const passwordError =
                document.getElementById(
                    "login-password-error"
                );

            const submitButton =
                loginForm.querySelector(
                    'button[type="submit"]'
                );

            let isValid = true;

            emailError.textContent = "";
            passwordError.textContent = "";

            if (email === "") {
                emailError.textContent =
                    "Email is required.";

                isValid = false;
            } else if (
                !/^[A-Za-z0-9._%+\-]+@columbia\.edu$/i
                    .test(email)
            ) {
                emailError.textContent =
                    "Please enter a valid @columbia.edu email address.";

                isValid = false;
            }

            if (password === "") {
                passwordError.textContent =
                    "Password is required.";

                isValid = false;
            }

            if (!isValid) {
                return;
            }

            submitButton.disabled = true;
            submitButton.textContent =
                "Signing In...";

            try {
                const response = await fetch(
                    "/api/login",
                    {
                        method: "POST",

                        headers: {
                            "Content-Type":
                                "application/json"
                        },

                        body: JSON.stringify({
                            email: email,
                            password: password
                        })
                    }
                );

                const data =
                    await response.json();

                if (!response.ok) {
                    if (
                        data.requiresVerification
                    ) {
                        window.location.href =
                            "/verify";

                        return;
                    }

                    throw new Error(
                        data.error ||
                        "Unable to log in."
                    );
                }

                window.location.href = "/";

            } catch (error) {
                console.error(error);

                passwordError.textContent =
                    error.message ||
                    "Unable to log in.";

            } finally {
                submitButton.disabled = false;
                submitButton.textContent =
                    "Login";
            }
        }
    );
}


// =========================================================
// Logout
// =========================================================

const logoutButton =
    document.getElementById("logout-button");

if (logoutButton) {
    logoutButton.addEventListener(
        "click",
        async function (event) {
            event.preventDefault();

            try {
                await fetch(
                    "/api/logout",
                    {
                        method: "POST"
                    }
                );
            } catch (error) {
                console.error(
                    "Logout request failed:",
                    error
                );
            } finally {
                window.location.href = "/login";
            }
        }
    );
}


// =========================================================
// Dashboard state
// =========================================================

let salesChart = null;
let marginChart = null;
let currentForecastRows = [];

const channelOrder = [
    "Stores",
    "E-commerce",
    "SWS"
];


// =========================================================
// Formatting helpers
// =========================================================

function formatChartCurrency(value) {
    return new Intl.NumberFormat(
        "en-US",
        {
            style: "currency",
            currency: "USD",
            notation: "compact",
            maximumFractionDigits: 2
        }
    ).format(value);
}


function formatDisplayDate(dateString) {
    const date = new Date(
        `${dateString}T00:00:00`
    );

    return date.toLocaleDateString(
        "en-US",
        {
            month: "short",
            day: "numeric"
        }
    );
}


function escapeCsvValue(value) {
    const text =
        value === null ||
        value === undefined
            ? ""
            : String(value);

    return `"${text.replace(/"/g, '""')}"`;
}


// =========================================================
// Channel cards
// =========================================================

function updateChannelCard(
    prefix,
    channelData
) {
    const salesElement =
        document.getElementById(
            `${prefix}-sales-value`
        );

    const marginElement =
        document.getElementById(
            `${prefix}-margin-value`
        );

    const marginRateElement =
        document.getElementById(
            `${prefix}-margin-rate-value`
        );

    if (
        !salesElement ||
        !marginElement ||
        !marginRateElement
    ) {
        return;
    }

    if (!channelData) {
        salesElement.textContent = "—";
        marginElement.textContent = "—";
        marginRateElement.textContent = "—";

        return;
    }

    salesElement.textContent =
        channelData.forecastSales || "—";

    marginElement.textContent =
        channelData.forecastMargin || "—";

    marginRateElement.textContent =
        channelData.marginRate || "—";
}


// =========================================================
// Forecast table
// =========================================================

function renderForecastTable(rows) {
    const forecastTableBody =
        document.getElementById(
            "forecast-table-body"
        );

    if (!forecastTableBody) {
        return;
    }

    forecastTableBody.innerHTML = "";

    if (!rows || rows.length === 0) {
        forecastTableBody.innerHTML = `
            <tr class="empty-row">
                <td colspan="5">
                    <div class="empty-table-state">
                        <div class="empty-table-icon">
                            —
                        </div>

                        <h3>
                            No forecast results available
                        </h3>

                        <p>
                            No forecast records were found
                            for the selected filters.
                        </p>
                    </div>
                </td>
            </tr>
        `;

        return;
    }

    rows.forEach(function (row) {
        const tableRow =
            document.createElement("tr");

        tableRow.innerHTML = `
            <td>${row.date}</td>
            <td>${row.channel}</td>
            <td>${row.forecastSales}</td>
            <td>${row.forecastMargin}</td>
            <td>${row.marginRate}</td>
        `;

        forecastTableBody.appendChild(
            tableRow
        );
    });
}


// =========================================================
// Chart data helpers
// =========================================================

function buildChartData(rows, rawField) {
    const dateSet = new Set();

    rows.forEach(function (row) {
        dateSet.add(row.date);
    });

    const dates =
        Array.from(dateSet).sort();

    const channels =
        channelOrder.filter(
            function (channel) {
                return rows.some(
                    function (row) {
                        return (
                            row.channel === channel
                        );
                    }
                );
            }
        );

    const datasets =
        channels.map(
            function (channel) {
                const rowsByDate = new Map();

                rows
                    .filter(
                        function (row) {
                            return (
                                row.channel === channel
                            );
                        }
                    )
                    .forEach(
                        function (row) {
                            rowsByDate.set(
                                row.date,
                                Number(
                                    row[rawField]
                                ) || 0
                            );
                        }
                    );

                return {
                    label: channel,
                    data: dates.map(
                        function (date) {
                            return (
                                rowsByDate.get(date)
                                ?? null
                            );
                        }
                    ),
                    borderWidth: 2,
                    pointRadius: 2,
                    pointHoverRadius: 5,
                    tension: 0.25,
                    spanGaps: true
                };
            }
        );

    return {
        labels: dates.map(
            formatDisplayDate
        ),
        datasets: datasets
    };
}


// =========================================================
// Charts
// =========================================================

function renderCharts(rows) {
    const salesCanvas =
        document.getElementById(
            "sales-chart"
        );

    const marginCanvas =
        document.getElementById(
            "margin-chart"
        );

    const salesEmptyState =
        document.getElementById(
            "sales-chart-empty-state"
        );

    const marginEmptyState =
        document.getElementById(
            "margin-chart-empty-state"
        );

    if (
        !salesCanvas ||
        !marginCanvas
    ) {
        return;
    }

    if (
        typeof Chart === "undefined"
    ) {
        throw new Error(
            "Chart.js could not be loaded. Check your internet connection and refresh the page."
        );
    }

    if (salesChart) {
        salesChart.destroy();
        salesChart = null;
    }

    if (marginChart) {
        marginChart.destroy();
        marginChart = null;
    }

    if (!rows || rows.length === 0) {
        salesCanvas.hidden = true;
        marginCanvas.hidden = true;

        if (salesEmptyState) {
            salesEmptyState.hidden = false;
        }

        if (marginEmptyState) {
            marginEmptyState.hidden = false;
        }

        return;
    }

    salesCanvas.hidden = false;
    marginCanvas.hidden = false;

    if (salesEmptyState) {
        salesEmptyState.hidden = true;
    }

    if (marginEmptyState) {
        marginEmptyState.hidden = true;
    }

    const salesChartData =
        buildChartData(
            rows,
            "forecastSalesRaw"
        );

    const marginChartData =
        buildChartData(
            rows,
            "forecastMarginRaw"
        );

    const commonOptions = {
        responsive: true,
        maintainAspectRatio: false,

        interaction: {
            mode: "index",
            intersect: false
        },

        plugins: {
            legend: {
                position: "top"
            },

            tooltip: {
                callbacks: {
                    label: function (context) {
                        const label =
                            context.dataset.label
                                ? `${context.dataset.label}: `
                                : "";

                        return (
                            label +
                            formatChartCurrency(
                                context.parsed.y
                            )
                        );
                    }
                }
            }
        },

        scales: {
            x: {
                title: {
                    display: true,
                    text: "Forecast Date"
                }
            },

            y: {
                beginAtZero: true,

                ticks: {
                    callback: function (value) {
                        return formatChartCurrency(
                            value
                        );
                    }
                }
            }
        }
    };

    salesChart = new Chart(
        salesCanvas,
        {
            type: "line",

            data: salesChartData,

            options: {
                ...commonOptions,

                scales: {
                    ...commonOptions.scales,

                    y: {
                        ...commonOptions.scales.y,

                        title: {
                            display: true,
                            text: "Forecast Sales"
                        }
                    }
                }
            }
        }
    );

    marginChart = new Chart(
        marginCanvas,
        {
            type: "line",

            data: marginChartData,

            options: {
                ...commonOptions,

                scales: {
                    ...commonOptions.scales,

                    y: {
                        ...commonOptions.scales.y,

                        title: {
                            display: true,
                            text: "Forecast Margin"
                        }
                    }
                }
            }
        }
    );
}


// =========================================================
// Dashboard rendering
// =========================================================

function renderDashboard(
    dashboardData,
    forecastData
) {
    document.getElementById(
        "forecast-sales-value"
    ).textContent =
        dashboardData.summary.forecastSales;

    document.getElementById(
        "forecast-margin-value"
    ).textContent =
        dashboardData.summary.forecastMargin;

    document.getElementById(
        "margin-rate-value"
    ).textContent =
        dashboardData.summary.marginRate;

    const selectedChannel =
        dashboardData.filters.channel;

    const selectedRange =
        `${dashboardData.filters.startDate} to ` +
        dashboardData.filters.endDate;

    const forecastSalesNote =
        document.getElementById(
            "forecast-sales-note"
        );

    const forecastMarginNote =
        document.getElementById(
            "forecast-margin-note"
        );

    const marginRateNote =
        document.getElementById(
            "margin-rate-note"
        );

    if (forecastSalesNote) {
        forecastSalesNote.textContent =
            `${selectedChannel} · ${selectedRange}`;
    }

    if (forecastMarginNote) {
        forecastMarginNote.textContent =
            `${selectedChannel} · ${selectedRange}`;
    }

    if (marginRateNote) {
        marginRateNote.textContent =
            "Forecast margin divided by forecast sales";
    }

    updateChannelCard(
        "stores",
        dashboardData.channels["Stores"]
    );

    updateChannelCard(
        "ecommerce",
        dashboardData.channels[
            "E-commerce"
            ]
    );

    updateChannelCard(
        "sws",
        dashboardData.channels["SWS"]
    );

    currentForecastRows =
        forecastData.rows || [];

    renderForecastTable(
        currentForecastRows
    );

    renderCharts(
        currentForecastRows
    );

    const lastUpdatedValue =
        document.getElementById(
            "last-updated-value"
        );

    if (lastUpdatedValue) {
        lastUpdatedValue.textContent =
            new Date(
                dashboardData.lastUpdated
            ).toLocaleString(
                "en-US"
            );
    }
}


// =========================================================
// Load dashboard data
// =========================================================

async function loadDashboard() {
    const dashboardFilterForm =
        document.getElementById(
            "dashboard-filter-form"
        );

    if (!dashboardFilterForm) {
        return;
    }

    const startDate =
        document.getElementById(
            "start-date"
        ).value;

    const endDate =
        document.getElementById(
            "end-date"
        ).value;

    const channel =
        document.getElementById(
            "channel-filter"
        ).value;

    const filterError =
        document.getElementById(
            "dashboard-filter-error"
        );

    const submitButton =
        dashboardFilterForm.querySelector(
            'button[type="submit"]'
        );

    filterError.textContent = "";

    if (
        startDate === "" ||
        endDate === ""
    ) {
        filterError.textContent =
            "Please select both a start date and an end date.";

        return;
    }

    if (endDate < startDate) {
        filterError.textContent =
            "End date cannot be earlier than start date.";

        return;
    }

    submitButton.disabled = true;
    submitButton.textContent = "Loading...";

    const queryParameters =
        new URLSearchParams({
            start_date: startDate,
            end_date: endDate,
            channel: channel
        });

    try {
        const [
            dashboardResponse,
            forecastResponse
        ] = await Promise.all([
            fetch(
                `/api/dashboard?${queryParameters.toString()}`
            ),

            fetch(
                `/api/forecast-results?${queryParameters.toString()}`
            )
        ]);

        const dashboardData =
            await dashboardResponse.json();

        const forecastData =
            await forecastResponse.json();

        if (!dashboardResponse.ok) {
            throw new Error(
                dashboardData.error ||
                "Unable to load dashboard data."
            );
        }

        if (!forecastResponse.ok) {
            throw new Error(
                forecastData.error ||
                "Unable to load forecast results."
            );
        }

        renderDashboard(
            dashboardData,
            forecastData
        );

    } catch (error) {
        console.error(error);

        filterError.textContent =
            error.message ||
            "Unable to connect to the server.";

    } finally {
        submitButton.disabled = false;
        submitButton.textContent =
            "Refresh Dashboard";
    }
}


// =========================================================
// Load available data range
// =========================================================

async function initializeDashboard() {
    const dashboardFilterForm =
        document.getElementById(
            "dashboard-filter-form"
        );

    if (!dashboardFilterForm) {
        return;
    }

    const filterError =
        document.getElementById(
            "dashboard-filter-error"
        );

    try {
        const response =
            await fetch("/api/data-range");

        const data =
            await response.json();

        if (!response.ok) {
            throw new Error(
                data.error ||
                "Unable to load the available data range."
            );
        }

        const startDateInput =
            document.getElementById(
                "start-date"
            );

        const endDateInput =
            document.getElementById(
                "end-date"
            );

        startDateInput.min =
            data.startDate;

        startDateInput.max =
            data.endDate;

        startDateInput.value =
            data.startDate;

        endDateInput.min =
            data.startDate;

        endDateInput.max =
            data.endDate;

        endDateInput.value =
            data.endDate;

        const startDate =
            new Date(
                `${data.startDate}T00:00:00`
            );

        const endDate =
            new Date(
                `${data.endDate}T00:00:00`
            );

        const horizonDays =
            Math.round(
                (
                    endDate - startDate
                ) /
                (
                    1000 *
                    60 *
                    60 *
                    24
                )
            ) + 1;

        const modelStartDateValue =
            document.getElementById(
                "model-start-date-value"
            );

        const forecastHorizonValue =
            document.getElementById(
                "forecast-horizon-value"
            );

        if (modelStartDateValue) {
            modelStartDateValue.textContent =
                startDate.toLocaleDateString(
                    "en-US",
                    {
                        month: "long",
                        day: "numeric",
                        year: "numeric"
                    }
                );
        }

        if (forecastHorizonValue) {
            forecastHorizonValue.textContent =
                `${horizonDays} Days`;
        }

        await loadDashboard();

    } catch (error) {
        console.error(error);

        filterError.textContent =
            error.message ||
            "Unable to initialize the dashboard.";
    }
}


// =========================================================
// Dashboard form
// =========================================================

const dashboardFilterForm =
    document.getElementById(
        "dashboard-filter-form"
    );

if (dashboardFilterForm) {
    dashboardFilterForm.addEventListener(
        "submit",
        async function (event) {
            event.preventDefault();
            await loadDashboard();
        }
    );
}


// =========================================================
// CSV download
// =========================================================

const downloadCsvButton =
    document.getElementById(
        "download-csv-button"
    );

if (downloadCsvButton) {
    downloadCsvButton.addEventListener(
        "click",
        function () {
            const filterError =
                document.getElementById(
                    "dashboard-filter-error"
                );

            if (
                !currentForecastRows ||
                currentForecastRows.length === 0
            ) {
                filterError.textContent =
                    "There is no forecast data to download.";

                return;
            }

            filterError.textContent = "";

            const headers = [
                "Date",
                "Channel",
                "Forecast Sales",
                "Forecast Margin",
                "Margin Rate"
            ];

            const csvRows = [
                headers.map(
                    escapeCsvValue
                ).join(",")
            ];

            currentForecastRows.forEach(
                function (row) {
                    csvRows.push(
                        [
                            row.date,
                            row.channel,
                            row.forecastSalesRaw,
                            row.forecastMarginRaw,
                            row.marginRateRaw
                        ]
                            .map(escapeCsvValue)
                            .join(",")
                    );
                }
            );

            const csvContent =
                csvRows.join("\n");

            const csvBlob =
                new Blob(
                    [csvContent],
                    {
                        type:
                            "text/csv;charset=utf-8;"
                    }
                );

            const downloadUrl =
                URL.createObjectURL(csvBlob);

            const downloadLink =
                document.createElement("a");

            const startDate =
                document.getElementById(
                    "start-date"
                ).value;

            const endDate =
                document.getElementById(
                    "end-date"
                ).value;

            downloadLink.href =
                downloadUrl;

            downloadLink.download =
                `jbs_forecast_${startDate}_${endDate}.csv`;

            document.body.appendChild(
                downloadLink
            );

            downloadLink.click();

            downloadLink.remove();

            URL.revokeObjectURL(
                downloadUrl
            );
        }
    );
}


// =========================================================
// Chart export
// =========================================================

function exportChart(
    chart,
    fileName
) {
    const filterError =
        document.getElementById(
            "dashboard-filter-error"
        );

    if (!chart) {
        filterError.textContent =
            "The chart is not available for export.";

        return;
    }

    filterError.textContent = "";

    const downloadLink =
        document.createElement("a");

    downloadLink.href =
        chart.toBase64Image(
            "image/png",
            1
        );

    downloadLink.download =
        fileName;

    document.body.appendChild(
        downloadLink
    );

    downloadLink.click();

    downloadLink.remove();
}


const exportSalesChartButton =
    document.getElementById(
        "export-sales-chart-button"
    );

if (exportSalesChartButton) {
    exportSalesChartButton.addEventListener(
        "click",
        function () {
            exportChart(
                salesChart,
                "jbs_forecast_sales_chart.png"
            );
        }
    );
}


const exportMarginChartButton =
    document.getElementById(
        "export-margin-chart-button"
    );

if (exportMarginChartButton) {
    exportMarginChartButton.addEventListener(
        "click",
        function () {
            exportChart(
                marginChart,
                "jbs_forecast_margin_chart.png"
            );
        }
    );
}


// =========================================================
// Automatically initialize dashboard
// =========================================================

document.addEventListener(
    "DOMContentLoaded",
    function () {
        if (
            document.getElementById(
                "dashboard-filter-form"
            )
        ) {
            initializeDashboard();
        }
    }
);

// =========================================================
// Forgot password page
// =========================================================

const forgotPasswordForm =
    document.getElementById(
        "forgot-password-form"
    );

if (forgotPasswordForm) {
    forgotPasswordForm.addEventListener(
        "submit",
        async function (event) {
            event.preventDefault();

            const email =
                document
                    .getElementById(
                        "forgot-password-email"
                    )
                    .value
                    .trim()
                    .toLowerCase();

            const emailError =
                document.getElementById(
                    "forgot-password-email-error"
                );

            const submitButton =
                forgotPasswordForm.querySelector(
                    'button[type="submit"]'
                );

            emailError.textContent = "";

            if (email === "") {
                emailError.textContent =
                    "Email is required.";

                return;
            }

            if (
                !/^[A-Za-z0-9._%+\-]+@columbia\.edu$/i
                    .test(email)
            ) {
                emailError.textContent =
                    "Please enter a valid @columbia.edu email address.";

                return;
            }

            submitButton.disabled = true;
            submitButton.textContent =
                "Sending Code...";

            try {
                const response = await fetch(
                    "/api/forgot-password",
                    {
                        method: "POST",

                        headers: {
                            "Content-Type":
                                "application/json"
                        },

                        body: JSON.stringify({
                            email: email
                        })
                    }
                );

                await readJsonResponse(response);

                window.location.href =
                    "/reset-password";

            } catch (error) {
                console.error(error);

                emailError.textContent =
                    error.message ||
                    "Unable to send the reset code.";

            } finally {
                submitButton.disabled = false;
                submitButton.textContent =
                    "Send Reset Code";
            }
        }
    );
}

// =========================================================
// Reset password page
// =========================================================

const resetPasswordForm =
    document.getElementById(
        "reset-password-form"
    );

if (resetPasswordForm) {
    resetPasswordForm.addEventListener(
        "submit",
        async function (event) {
            event.preventDefault();

            const resetCode =
                document
                    .getElementById(
                        "reset-code"
                    )
                    .value
                    .trim();

            const newPassword =
                document
                    .getElementById(
                        "new-password"
                    )
                    .value;

            const confirmNewPassword =
                document
                    .getElementById(
                        "confirm-new-password"
                    )
                    .value;

            const resetCodeError =
                document.getElementById(
                    "reset-code-error"
                );

            const newPasswordError =
                document.getElementById(
                    "new-password-error"
                );

            const confirmPasswordError =
                document.getElementById(
                    "confirm-new-password-error"
                );

            const submitButton =
                resetPasswordForm.querySelector(
                    'button[type="submit"]'
                );

            let isValid = true;

            resetCodeError.textContent = "";
            newPasswordError.textContent = "";
            confirmPasswordError.textContent = "";

            if (!/^\d{6}$/.test(resetCode)) {
                resetCodeError.textContent =
                    "Please enter a valid 6-digit code.";

                isValid = false;
            }

            if (newPassword === "") {
                newPasswordError.textContent =
                    "New password is required.";

                isValid = false;

            } else if (newPassword.length < 8) {
                newPasswordError.textContent =
                    "Password must contain at least 8 characters.";

                isValid = false;

            } else if (
                !/[A-Z]/.test(newPassword) ||
                !/[a-z]/.test(newPassword) ||
                !/[0-9]/.test(newPassword)
            ) {
                newPasswordError.textContent =
                    "Password must include uppercase, lowercase, and a number.";

                isValid = false;
            }

            if (confirmNewPassword === "") {
                confirmPasswordError.textContent =
                    "Please confirm your new password.";

                isValid = false;

            } else if (
                newPassword !== confirmNewPassword
            ) {
                confirmPasswordError.textContent =
                    "Passwords do not match.";

                isValid = false;
            }

            if (!isValid) {
                return;
            }

            submitButton.disabled = true;
            submitButton.textContent =
                "Resetting Password...";

            try {
                const response = await fetch(
                    "/api/reset-password",
                    {
                        method: "POST",

                        headers: {
                            "Content-Type":
                                "application/json"
                        },

                        body: JSON.stringify({
                            code: resetCode,
                            password: newPassword
                        })
                    }
                );

                const data =
                    await readJsonResponse(response);

                alert(
                    data.message ||
                    "Password reset successfully."
                );

                window.location.href = "/login";

            } catch (error) {
                console.error(error);

                resetCodeError.textContent =
                    error.message ||
                    "Unable to reset the password.";

            } finally {
                submitButton.disabled = false;
                submitButton.textContent =
                    "Reset Password";
            }
        }
    );
}