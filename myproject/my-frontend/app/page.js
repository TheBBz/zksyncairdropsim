"use client";

import { useState, useEffect } from 'react';
import '../styles/global.css';
import '@sakun/system.css';
import { analyzeWallet } from '../utils/api'; // Ensure this import is correct

export default function Home() {
    const [walletAddress, setWalletAddress] = useState('');
    const [results, setResults] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [showSupportUs, setShowSupportUs] = useState(false);

    const handleAnalyze = async () => {
        console.log("Fetch button clicked"); // Debug log
        setLoading(true);
        setError(null);
        setResults(null);
        setShowSupportUs(false); // Hide Support Us window when fetching new data
        try {
            const result = await analyzeWallet(walletAddress);
            console.log("API response:", result); // Debug log
            setResults(result);
            setShowSupportUs(true); // Show Support Us window after results are obtained
        } catch (err) {
            console.error("Error analyzing wallet:", err); // Debug log
            setError('Error analyzing wallet.');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        document.title = "zkSync Airdrop Simulator";
    }, []);

    return (
        <div className="container">
            <div className="window">
                <div className="title-bar">
                    <button aria-label="Close" className="close"></button>
                    <div className="title-container">
                        <h1 className="title">zkSync Airdrop Simulator</h1>
                    </div>
                    <button aria-label="Resize" className="resize"></button>
                </div>
                <div className="separator"></div>

                <div className="window-pane">
                    <section className="field-row" style={{ justifyContent: 'flex-start' }}>
                        <label htmlFor="wallet_address" className="modeless-text">Wallet Address:</label>
                        <input id="wallet_address" type="text" style={{ width: '100%' }} placeholder="Enter your wallet address" value={walletAddress} onChange={(e) => setWalletAddress(e.target.value)} />
                    </section>
                    <section className="field-row" style={{ justifyContent: 'flex-end' }}>
                        <button id="analyze_button" className="btn" style={{ width: '95px' }} onClick={handleAnalyze}>Fetch</button>
                    </section>
                </div>
            </div>

            {showSupportUs && (
                <div className="window donations">
                    <div className="title-bar">
                        <button aria-label="Close" className="close"></button>
                        <h1 className="title">Support Us</h1>
                        <button aria-label="Resize" className="resize"></button>
                    </div>
                    <div className="separator"></div>

                    <div className="window-pane">
                        <p>If you enjoy using this tool, please consider sending a donation through zkSync network to:</p>
                        <p>0xcc0Ff1d8CB212363AbD32bFC6eee7602f7a84A0d</p>
                    </div>
                </div>
            )}

            <div className="window results-window" id="results_window" style={{ display: results || loading ? 'block' : 'none' }}>
                <div className="title-bar">
                    <button aria-label="Close" className="close"></button>
                    <h1 className="title">Results</h1>
                    <button aria-label="Resize" disabled className="hidden"></button>
                </div>
                <div className="separator"></div>

                <div className="window-pane" id="results">
                    {loading && <p>Loading...</p>}
                    {error && <p>{error}</p>}
                    {results && (
                        <div>
                            <p>ETH to USD rate: ${results.eth_to_usd_rate}</p>
                            <p>ZKS: {results.zks}</p>
                            <p>Eligibility: {results.is_eligible ? 'Eligible' : 'Not Eligible'}</p>
                            <p>Details:</p>
                            <ul>
                                {results.details.map((detail, index) => <li key={index}>{detail}</li>)}
                            </ul>
                            <p>zkSync Lite Activity: {results.zksync_lite_activity ? 'Yes' : 'No'}</p>
                        </div>
                    )}
                </div>
            </div>

            <div className="window how-it-works">
                <div className="title-bar">
                    <button aria-label="Close" className="close"></button>
                    <h1 className="title">How it Works</h1>
                    <button aria-label="Resize" className="resize"></button>
                </div>
                <div className="separator"></div>

                <div className="window-pane">
                    <p>Enter your wallet address to check your eligibility for airdrops. The analyzer will fetch your transaction history and current balance, then calculate your eligibility based on the GitHub zkSync rumors regarding the criteria. Beware this is not official criteria.</p>
                    <img src="/images/GOJLRY7WwAA7258.jpeg" alt="How it Works" />
                </div>
            </div>
        </div>
    );
}
