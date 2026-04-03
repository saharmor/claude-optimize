import { BrowserRouter, Link, Route, Routes, useNavigate } from "react-router-dom";
import ScanInput from "./pages/ScanInput";
import Report from "./pages/Report";
import History from "./pages/History";
import "./App.css";

function NotFound() {
  const navigate = useNavigate();
  return (
    <div style={{ textAlign: "center", padding: "4rem 1rem" }}>
      <h2>Page not found</h2>
      <p style={{ color: "var(--muted-foreground)", marginTop: "0.5rem" }}>
        The page you're looking for doesn't exist.
      </p>
      <button
        type="button"
        className="btn btn-primary"
        style={{ marginTop: "1.5rem" }}
        onClick={() => navigate("/")}
      >
        Go home
      </button>
    </div>
  );
}

function App() {
  return (
    <BrowserRouter>
      <div className="app-shell">
        <header className="topbar">
          <div className="topbar-inner">
            <Link to="/" className="brand-link">
              <svg className="brand-mark" width="20" height="20" viewBox="0 0 96 96" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M48 8C50 28 68 46 88 48C68 50 50 68 48 88C46 68 28 50 8 48C28 46 46 28 48 8Z" fill="currentColor"/>
                <path d="M76 4C77 12 83 18 91 19C83 20 77 26 76 34C75 26 69 20 61 19C69 18 75 12 76 4Z" fill="currentColor" opacity="0.7"/>
                <path d="M22 62C23 68 27.5 72.5 33.5 73.5C27.5 74.5 23 79 22 85C21 79 16.5 74.5 10.5 73.5C16.5 72.5 21 68 22 62Z" fill="currentColor" opacity="0.5"/>
              </svg>
              <span className="brand-text">Claude Optimize</span>
            </Link>
            <div className="topbar-right">
              <Link to="/history" className="topbar-link">History</Link>
            </div>
          </div>
        </header>

        <main className="page-shell">
          <Routes>
            <Route path="/" element={<ScanInput />} />
            <Route path="/report/:scanId" element={<Report />} />
            <Route path="/history" element={<History />} />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </main>

        <footer className="site-footer">
          <div className="site-footer-inner">
            <div>
              <div className="site-footer-title">Claude Optimize</div>
              <p className="site-footer-copy">
                Review a Claude-powered codebase with parallel analyzers and turn
                the output into a clear optimization audit.
              </p>
            </div>
          </div>
        </footer>
      </div>
    </BrowserRouter>
  );
}

export default App;
