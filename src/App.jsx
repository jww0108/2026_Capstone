import { useState, useRef } from "react";
import { STEPS } from './constants/steps';
import { buildData } from './utils/buildData';
import LandingPage from './pages/LandingPage';
import LoadingPage from './pages/LoadingPage';
import SummaryPage from './pages/SummaryPage';
import OverviewPage from './pages/OverviewPage';
import ProfilePage from './pages/ProfilePage';
import MarketPage from './pages/MarketPage';
import CareerPage from './pages/CareerPage';
import Sidebar from './components/Sidebar';

export default function App() {
  const [phase,    setPhase]    = useState("landing");
  const [username, setUsername] = useState("");
  const [loadPct,  setLoadPct]  = useState(0);
  const [loadStep, setLoadStep] = useState(0);
  const [section,  setSection]  = useState("overview");
  const [data,     setData]     = useState(null);
  const timerRef = useRef(null);

  const startAnalysis = () => {
    const u = username.trim();
    if (!u) return;
    setPhase("loading");
    setLoadPct(0);
    setLoadStep(0);
    let pct = 0;
    timerRef.current = setInterval(() => {
      pct += Math.random() * 4.5 + 1.5;
      setLoadStep(Math.min(Math.floor(pct / (100 / STEPS.length)), STEPS.length - 1));
      setLoadPct(Math.min(pct, 99));
      if (pct >= 99) {
        clearInterval(timerRef.current);
        setLoadPct(100);
        setData(buildData(u));
        setTimeout(() => setPhase("summary"), 700);
      }
    }, 170);
  };

  /* LANDING */
  if (phase === "landing") {
    return (
      <LandingPage
        username={username}
        setUsername={setUsername}
        onStart={startAnalysis}
      />
    );
  }

  /* LOADING */
  if (phase === "loading") {
    return (
      <LoadingPage
        username={username}
        loadPct={loadPct}
        loadStep={loadStep}
      />
    );
  }

  /* SUMMARY */
  if (phase === "summary") {
    return (
      <SummaryPage
        username={username}
        data={data}
        onDetail={() => { setSection("overview"); setPhase("detail"); }}
        onReset={() => { setPhase("landing"); setUsername(""); }}
      />
    );
  }

  /* DETAIL */
  const pages = {
    overview: <OverviewPage username={username} data={data} />,
    profile:  <ProfilePage />,
    market:   <MarketPage data={data} />,
    career:   <CareerPage data={data} />,
  };
  return (
    <div style={{ display:"flex", minHeight:"100vh" }}>
      <Sidebar active={section} onSelect={setSection} />
      {pages[section]}
    </div>
  );
}
