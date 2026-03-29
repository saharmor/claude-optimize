import { BrowserRouter, Link, Route, Routes } from "react-router-dom";
import ScanInput from "./pages/ScanInput";
import ScanProgress from "./pages/ScanProgress";
import Report from "./pages/Report";
import "./App.css";

function App() {
  return (
    <BrowserRouter>
      <div className="app-shell">
        <header className="topbar">
          <div className="topbar-inner">
            <Link to="/" className="brand-link">
              <span className="brand-mark">&#9672;</span>
              <span className="brand-text">Claude Optimize</span>
            </Link>
            <div className="topbar-copy">
              Claude-native audit for cost, latency, and reliability improvements
            </div>
          </div>
        </header>

        <main className="page-shell">
          <Routes>
            <Route path="/" element={<ScanInput />} />
            <Route path="/scan/:scanId" element={<ScanProgress />} />
            <Route path="/report/:scanId" element={<Report />} />
          </Routes>
        </main>

        <footer className="site-footer">
          <div className="site-footer-inner">
            <div>
              <div className="site-footer-title">Claude Optimize</div>
              <p className="site-footer-copy">
                Review a Claude-powered codebase with parallel analyzers and turn
                the output into a clear optimization report.
              </p>
            </div>
          </div>
        </footer>
      </div>
    </BrowserRouter>
  );
}

export default App;
