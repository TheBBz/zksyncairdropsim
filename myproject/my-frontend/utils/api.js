import axios from 'axios';

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL, // Ensure this is set in your .env.local file
});

export const analyzeWallet = async (walletAddress) => {
  const response = await api.post('/api/analyze', {
    wallet_address: walletAddress,
  });
  return response.data;
};
