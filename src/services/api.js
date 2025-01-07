import axios from 'axios';

// If you don't use a proxy in package.json, specify full URL:
// e.g. const API_BASE = 'http://localhost:5000';
// If you use "proxy": "http://localhost:5000" in package.json,
// you can just do: const API_BASE = '';
const API_BASE = 'http://localhost:5000';

export const startLearning = async (seed) => {
  const response = await axios.get(`${API_BASE}/start`, {
    params: { seed },
  });
  return response.data;
};

export const getPhase1Data = async () => {
  const response = await axios.get(`${API_BASE}/phase1`);
  return response.data;
};

export const getPhase2Data = async () => {
  const response = await axios.get(`${API_BASE}/phase2`);
  return response.data;
};

export const checkAnswer = async (payload) => {
  const response = await axios.post(`${API_BASE}/check_answer`, payload);
  return response.data;
};

export const nextPhase = async () => {
  const response = await axios.post(`${API_BASE}/next_phase`);
  return response.data;
};

export const getSound = async () => {
  const response = await axios.get(`${API_BASE}/getSound`);
  return response.data;
};
