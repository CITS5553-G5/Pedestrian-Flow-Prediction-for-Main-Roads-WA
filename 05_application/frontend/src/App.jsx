import { useMemo, useState } from "react";
import "./App.css";

function App() {
  const [formData, setFormData] = useState({
    location: "Perth CBD",
    date: "",
    time: "",
    dayType: "Weekday",
    weather: "Clear",
  });

  const [prediction, setPrediction] = useState({
    count: 1248,
    level: "High",
    confidence: 94,
    peakTime: "17:30",
  });

  const [loading, setLoading] = useState(false);
  const [activeSection, setActiveSection] = useState("dashboard");

  const [history, setHistory] = useState([
    {
      location: "Perth CBD",
      date: "25 Aug 2026",
      time: "17:30",
      count: 1248,
      level: "High",
    },
    {
      location: "Albany Highway",
      date: "24 Aug 2026",
      time: "15:00",
      count: 700,
      level: "Moderate",
    },
    {
      location: "Mitchell Freeway",
      date: "23 Aug 2026",
      time: "11:30",
      count: 450,
      level: "Low",
    },
  ]);

  const chartData = useMemo(
    () => [
      { time: "06:00", value: 38 },
      { time: "08:00", value: 58 },
      { time: "10:00", value: 47 },
      { time: "12:00", value: 70 },
      { time: "14:00", value: 82 },
      { time: "16:00", value: 94 },
      { time: "18:00", value: 76 },
      { time: "20:00", value: 52 },
    ],
    []
  );

  const handleChange = (event) => {
    const { name, value } = event.target;

    setFormData((previous) => ({
      ...previous,
      [name]: value,
    }));
  };

  const goToSection = (section) => {
    setActiveSection(section);

    const element = document.getElementById(section);

    if (element) {
      element.scrollIntoView({
        behavior: "smooth",
        block: "start",
      });
    }
  };

  const formatDate = (dateValue) => {
    if (!dateValue) return "Not selected";

    const date = new Date(`${dateValue}T00:00:00`);

    return date.toLocaleDateString("en-AU", {
      day: "2-digit",
      month: "short",
      year: "numeric",
    });
  };

  const handlePrediction = () => {
    setLoading(true);

    setTimeout(() => {
      const hour = formData.time
        ? Number(formData.time.split(":")[0])
        : 17;

      let baseCount = 700;

      if (hour >= 7 && hour <= 9) {
        baseCount = 1080;
      }

      if (hour >= 16 && hour <= 18) {
        baseCount = 1380;
      }

      if (formData.dayType === "Weekend") {
        baseCount += 160;
      }

      if (formData.dayType === "Public Holiday") {
        baseCount += 230;
      }

      if (formData.weather === "Rainy") {
        baseCount -= 250;
      }

      if (formData.weather === "Cloudy") {
        baseCount -= 80;
      }

      if (formData.location === "Perth CBD") {
        baseCount += 120;
      }

      if (formData.location === "Albany Highway") {
        baseCount -= 60;
      }

      if (formData.location === "Great Eastern Highway") {
        baseCount += 40;
      }

      if (formData.location === "Mitchell Freeway") {
        baseCount += 90;
      }

      if (formData.location === "Tonkin Highway") {
        baseCount += 55;
      }

      if (formData.location === "Stirling Highway") {
        baseCount += 20;
      }

      const predictedCount = Math.max(baseCount, 100);

      let flowLevel = "Low";

      if (predictedCount >= 1000) {
        flowLevel = "High";
      } else if (predictedCount >= 600) {
        flowLevel = "Moderate";
      }

      const newPrediction = {
        count: predictedCount,
        level: flowLevel,
        confidence: 94,
        peakTime: formData.time || "17:30",
      };

      setPrediction(newPrediction);

      setHistory((previous) => [
        {
          location: formData.location,
          date: formatDate(formData.date),
          time: formData.time || "17:30",
          count: predictedCount,
          level: flowLevel,
        },
        ...previous,
      ]);

      setLoading(false);
    }, 700);
  };

  const downloadResult = () => {
    const result = `
Pedestrian Flow Prediction
--------------------------
Location: ${formData.location}
Date: ${formData.date || "Not selected"}
Time: ${formData.time || "Not selected"}
Day Type: ${formData.dayType}
Weather: ${formData.weather}

Predicted Pedestrians: ${prediction.count}
Flow Level: ${prediction.level}
Confidence: ${prediction.confidence}%
Peak Time: ${prediction.peakTime}
`;

    const blob = new Blob([result], {
      type: "text/plain",
    });

    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");

    anchor.href = url;
    anchor.download = "pedestrian-flow-prediction.txt";

    document.body.appendChild(anchor);
    anchor.click();

    document.body.removeChild(anchor);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="logo-area">
          <div className="logo-box">PF</div>

          <div>
            <h2>PedFlow</h2>
            <p>Main Roads WA</p>
          </div>
        </div>

        <div className="menu-title">MAIN MENU</div>

        <nav className="sidebar-nav">
          <button
            className={`nav-button ${
              activeSection === "dashboard" ? "active" : ""
            }`}
            onClick={() => goToSection("dashboard")}
          >
            <span className="nav-icon">▦</span>
            Dashboard
          </button>

          <button
            className={`nav-button ${
              activeSection === "prediction" ? "active" : ""
            }`}
            onClick={() => goToSection("prediction")}
          >
            <span className="nav-icon">◎</span>
            Prediction
          </button>

          <button
            className={`nav-button ${
              activeSection === "analytics" ? "active" : ""
            }`}
            onClick={() => goToSection("analytics")}
          >
            <span className="nav-icon">⌁</span>
            Analytics
          </button>

          <button
            className={`nav-button ${
              activeSection === "history" ? "active" : ""
            }`}
            onClick={() => goToSection("history")}
          >
            <span className="nav-icon">◷</span>
            History
          </button>
        </nav>

        <div className="sidebar-card">
          <div className="model-indicator">
            <span></span>
            Model Online
          </div>

          <p>
            Prediction service is currently available and ready for requests.
          </p>
        </div>

        <div className="sidebar-footer">
          <p>Pedestrian Flow Prediction</p>
          <span>Project Version 1.0</span>
        </div>
      </aside>

      <main className="main">
        <header className="topbar" id="dashboard">
          <div>
            <p className="eyebrow">SMART TRAFFIC ANALYTICS</p>

            <h1>Pedestrian Flow Dashboard</h1>

            <p className="topbar-description">
              Predict pedestrian movement and analyse flow patterns across
              Main Roads Western Australia.
            </p>
          </div>

          <div className="top-actions">
            <div className="live-status">
              <span className="live-dot"></span>
              Model Ready
            </div>

            <div className="profile">
              <div className="profile-avatar">WA</div>

              <div>
                <strong>Main Roads</strong>
                <span>Analytics Portal</span>
              </div>
            </div>
          </div>
        </header>

        <section className="stats-grid">
          <article className="stat-card">
            <div className="stat-top">
              <span>Current Prediction</span>
              <div className="stat-icon">↗</div>
            </div>

            <h3>{prediction.count.toLocaleString()}</h3>
            <p>Pedestrians / hour</p>

            <div className="trend positive">+12.4% from average</div>
          </article>

          <article className="stat-card">
            <div className="stat-top">
              <span>Flow Level</span>
              <div className="stat-icon">◉</div>
            </div>

            <h3>{prediction.level}</h3>
            <p>Current traffic condition</p>

            <div
              className={`flow-pill ${prediction.level.toLowerCase()}`}
            >
              {prediction.level} Flow
            </div>
          </article>

          <article className="stat-card">
            <div className="stat-top">
              <span>Peak Time</span>
              <div className="stat-icon">◷</div>
            </div>

            <h3>{prediction.peakTime}</h3>
            <p>Expected maximum flow</p>

            <div className="trend">Evening peak period</div>
          </article>

          <article className="stat-card">
            <div className="stat-top">
              <span>Model Confidence</span>
              <div className="stat-icon">✓</div>
            </div>

            <h3>{prediction.confidence}%</h3>
            <p>Prediction confidence</p>

            <div className="confidence-bar">
              <span
                style={{
                  width: `${prediction.confidence}%`,
                }}
              ></span>
            </div>
          </article>
        </section>

        <section className="content-grid" id="prediction">
          <article className="glass-card prediction-card">
            <div className="card-heading">
              <div>
                <p className="eyebrow">NEW PREDICTION</p>
                <h2>Prediction Inputs</h2>
                <p>
                  Select the required parameters to estimate pedestrian flow.
                </p>
              </div>

              <div className="heading-icon">◎</div>
            </div>

            <div className="form-grid">
              <div className="field full-width">
                <label>Road / Location</label>

                <select
                  name="location"
                  value={formData.location}
                  onChange={handleChange}
                >
                  <option>Perth CBD</option>
                  <option>Albany Highway</option>
                  <option>Great Eastern Highway</option>
                  <option>Mitchell Freeway</option>
                  <option>Tonkin Highway</option>
                  <option>Stirling Highway</option>
                </select>
              </div>

              <div className="field">
                <label>Date</label>

                <input
                  type="date"
                  name="date"
                  value={formData.date}
                  onChange={handleChange}
                />
              </div>

              <div className="field">
                <label>Time</label>

                <input
                  type="time"
                  name="time"
                  value={formData.time}
                  onChange={handleChange}
                />
              </div>

              <div className="field">
                <label>Day Type</label>

                <select
                  name="dayType"
                  value={formData.dayType}
                  onChange={handleChange}
                >
                  <option>Weekday</option>
                  <option>Weekend</option>
                  <option>Public Holiday</option>
                </select>
              </div>

              <div className="field">
                <label>Weather Condition</label>

                <select
                  name="weather"
                  value={formData.weather}
                  onChange={handleChange}
                >
                  <option>Clear</option>
                  <option>Cloudy</option>
                  <option>Rainy</option>
                </select>
              </div>
            </div>

            <button
              className="predict-button"
              onClick={handlePrediction}
              disabled={loading}
            >
              {loading ? (
                <>
                  <span className="loader"></span>
                  Analysing Pedestrian Flow...
                </>
              ) : (
                <>
                  <span>✦</span>
                  Run Prediction
                </>
              )}
            </button>
          </article>

          <article className="glass-card result-card">
            <div className="result-top">
              <div>
                <p className="eyebrow">PREDICTION RESULT</p>
                <h2>Estimated Flow</h2>
              </div>

              <span className="result-live">LIVE</span>
            </div>

            <div className="result-main">
              <span className="result-caption">
                Predicted Pedestrians
              </span>

              <div className="result-number">
                {prediction.count.toLocaleString()}
              </div>

              <p>pedestrians per hour</p>

              <div
                className={`large-flow-pill ${prediction.level.toLowerCase()}`}
              >
                {prediction.level.toUpperCase()} FLOW
              </div>
            </div>

            <div className="result-info-grid">
              <div>
                <span>Confidence</span>
                <strong>{prediction.confidence}%</strong>
              </div>

              <div>
                <span>Peak Time</span>
                <strong>{prediction.peakTime}</strong>
              </div>
            </div>

            <div className="result-progress">
              <div className="progress-label">
                <span>Traffic intensity</span>
                <span>{prediction.level}</span>
              </div>

              <div className="progress-track">
                <span
                  style={{
                    width:
                      prediction.level === "High"
                        ? "88%"
                        : prediction.level === "Moderate"
                        ? "60%"
                        : "32%",
                  }}
                ></span>
              </div>
            </div>

            <button
              className="download-button"
              onClick={downloadResult}
            >
              ↓ Download Prediction Result
            </button>
          </article>
        </section>

        <section
          className="glass-card analytics-card"
          id="analytics"
        >
          <div className="analytics-header">
            <div>
              <p className="eyebrow">FLOW ANALYTICS</p>
              <h2>Pedestrian Flow Trend</h2>
              <p>
                Estimated pedestrian activity throughout the day.
              </p>
            </div>

            <div className="chart-filter">Today</div>
          </div>

          <div className="chart-area">
            <div className="y-axis">
              <span>1500</span>
              <span>1200</span>
              <span>900</span>
              <span>600</span>
              <span>300</span>
              <span>0</span>
            </div>

            <div className="chart-content">
              <div className="grid-lines">
                <span></span>
                <span></span>
                <span></span>
                <span></span>
                <span></span>
              </div>

              <div className="bars">
                {chartData.map((item) => (
                  <div
                    className="bar-column"
                    key={item.time}
                  >
                    <div className="bar-wrapper">
                      <div
                        className="bar"
                        style={{
                          height: `${item.value}%`,
                        }}
                      >
                        <div className="bar-tooltip">
                          {Math.round((item.value / 100) * 1500)}
                        </div>
                      </div>
                    </div>

                    <span>{item.time}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        <section
          className="glass-card history-card"
          id="history"
        >
          <div className="analytics-header">
            <div>
              <p className="eyebrow">RECENT ACTIVITY</p>
              <h2>Prediction History</h2>
              <p>
                Previously generated pedestrian flow predictions.
              </p>
            </div>

            <div className="chart-filter">Recent</div>
          </div>

          <div className="history-table">
            <div className="history-row history-header">
              <span>Location</span>
              <span>Date</span>
              <span>Time</span>
              <span>Prediction</span>
              <span>Flow</span>
            </div>

            {history.map((item, index) => (
              <div
                className="history-row"
                key={`${item.location}-${item.time}-${index}`}
              >
                <span>{item.location}</span>
                <span>{item.date}</span>
                <span>{item.time}</span>
                <span>{item.count.toLocaleString()}</span>

                <span
                  className={`history-${item.level.toLowerCase()}`}
                >
                  {item.level}
                </span>
              </div>
            ))}
          </div>
        </section>

        <footer className="footer">
          <p>
            Pedestrian Flow Prediction for Main Roads WA
          </p>

          <span>Data-driven pedestrian analytics</span>
        </footer>
      </main>
    </div>
  );
}

export default App;