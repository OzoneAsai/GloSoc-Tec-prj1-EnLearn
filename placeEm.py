import os

# プロジェクトのルートディレクトリ名
PROJECT_NAME = "GloSoc&Tec-prj1-EnLearn"

# ディレクトリとファイルの構造を辞書で定義
structure = {
    "public": {
        "index.html": """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Interactive Learning Tool</title>
</head>
<body>
    <div id="root"></div>
</body>
</html>
"""
    },
    "src": {
        "components": {
            "AudioPlayer.jsx": """import React from 'react';

const AudioPlayer = ({ src }) => {
    return (
        <div>
            <audio controls>
                <source src={src} type="audio/mpeg" />
                Your browser does not support the audio element.
            </audio>
        </div>
    );
};

export default AudioPlayer;
""",
            "Phase1Reading.jsx": """import React from 'react';
import AudioPlayer from './AudioPlayer';

const Phase1Reading = ({ rows, soundUrl }) => {
    return (
        <div>
            <h2>Phase1: Listen and Read</h2>
            <AudioPlayer src={soundUrl} />
            <ul>
                {rows.map((item, index) => (
                    <li key={index}>
                        <strong>English:</strong> {item.English}<br />
                        <strong>Japanese:</strong> {item.Japanese}
                    </li>
                ))}
            </ul>
        </div>
    );
};

export default Phase1Reading;
""",
            "Phase2Masking.jsx": """import React, { useState } from 'react';
import axios from '../services/api';

const Phase2Masking = ({ maskedRows }) => {
    const [answers, setAnswers] = useState({});
    const [feedback, setFeedback] = useState(null);

    const handleChange = (e, index, field) => {
        setAnswers({
            ...answers,
            [index]: {
                ...answers[index],
                [field]: e.target.value
            }
        });
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        try {
            const payload = {
                answers: Object.values(answers)
            };
            const response = await axios.checkAnswer(payload);
            setFeedback(response.feedback);
        } catch (error) {
            console.error("Error checking answers:", error);
        }
    };

    return (
        <div>
            <h2>Phase2: Fill in the Blanks</h2>
            <form onSubmit={handleSubmit}>
                {maskedRows.map((item, index) => (
                    <div key={index}>
                        <p>{item.masked_english}</p>
                        <input
                            type="text"
                            placeholder="Your answer"
                            value={answers[index]?.word || ''}
                            onChange={(e) => handleChange(e, index, 'word')}
                        />
                    </div>
                ))}
                <button type="submit">Submit Answers</button>
            </form>
            {feedback && <div>{feedback}</div>}
        </div>
    );
};

export default Phase2Masking;
"""
        },
        "pages": {
            "StartPage.jsx": """import React from 'react';
import { useNavigate } from 'react-router-dom';
import { startLearning } from '../services/api';

const StartPage = () => {
    const navigate = useNavigate();

    const handleStart = async () => {
        try {
            const response = await startLearning(42); // シード値を指定
            navigate('/phase1');
        } catch (error) {
            console.error("Error starting learning:", error);
        }
    };

    return (
        <div>
            <h1>Welcome to the Interactive Learning Tool</h1>
            <button onClick={handleStart}>Start Learning</button>
        </div>
    );
};

export default StartPage;
""",
            "Phase1Page.jsx": """import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { getPhase1Data } from '../services/api';
import Phase1Reading from '../components/Phase1Reading';

const Phase1Page = () => {
    const [rows, setRows] = useState([]);
    const [soundUrl, setSoundUrl] = useState(null);
    const navigate = useNavigate();

    useEffect(() => {
        const fetchData = async () => {
            try {
                const data = await getPhase1Data();
                setRows(data.rows);
                // ダミーの音声URLを設定
                setSoundUrl(null); // 実際にはdata.sound_urlを設定
            } catch (error) {
                console.error("Error fetching Phase1 data:", error);
            }
        };
        fetchData();
    }, []);

    const handleNext = () => {
        navigate('/phase2');
    };

    return (
        <div>
            <Phase1Reading rows={rows} soundUrl={soundUrl} />
            <button onClick={handleNext}>Next Phase</button>
        </div>
    );
};

export default Phase1Page;
""",
            "Phase2Page.jsx": """import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { getPhase2Data, nextPhase } from '../services/api';
import Phase2Masking from '../components/Phase2Masking';

const Phase2Page = () => {
    const [maskedRows, setMaskedRows] = useState([]);
    const navigate = useNavigate();

    useEffect(() => {
        const fetchMaskedData = async () => {
            try {
                const data = await getPhase2Data();
                setMaskedRows(data.rows);
            } catch (error) {
                console.error("Error fetching Phase2 data:", error);
            }
        };
        fetchMaskedData();
    }, []);

    const handleNext = async () => {
        try {
            const response = await nextPhase();
            if (response.phase === 1) {
                navigate('/phase1');
            } else {
                navigate('/summary');
            }
        } catch (error) {
            console.error("Error moving to next phase:", error);
        }
    };

    return (
        <div>
            <Phase2Masking maskedRows={maskedRows} />
            <button onClick={handleNext}>Next Phase</button>
        </div>
    );
};

export default Phase2Page;
""",
            "SummaryPage.jsx": """import React from 'react';
import { useNavigate } from 'react-router-dom';

const SummaryPage = () => {
    const navigate = useNavigate();

    const handleRestart = () => {
        navigate('/start');
    };

    return (
        <div>
            <h2>Congratulations! You've completed the training.</h2>
            <button onClick={handleRestart}>Restart Learning</button>
        </div>
    );
};

export default SummaryPage;
"""
        },
        "routes": {
            "AppRoutes.jsx": """import React from 'react';
import { Routes, Route } from 'react-router-dom';
import StartPage from '../pages/StartPage.jsx';
import Phase1Page from '../pages/Phase1Page.jsx';
import Phase2Page from '../pages/Phase2Page.jsx';
import SummaryPage from '../pages/SummaryPage.jsx';

const AppRoutes = () => {
    return (
        <Routes>
            <Route path="/" element={<StartPage />} />
            <Route path="/phase1" element={<Phase1Page />} />
            <Route path="/phase2" element={<Phase2Page />} />
            <Route path="/summary" element={<SummaryPage />} />
        </Routes>
    );
};

export default AppRoutes;
"""
        },
        "services": {
            "api.js": """import axios from 'axios';

const API_BASE = "http://localhost:5000"; // FlaskサーバーのURL

export const startLearning = async (seed) => {
    const response = await axios.get(`${API_BASE}/start`, { params: { seed } });
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
"""
        },
        "context": {
            "AppContext.js": """import React, { createContext, useState } from 'react';

export const AppContext = createContext();

const AppContextProvider = ({ children }) => {
    const [state, setState] = useState({
        // グローバルな状態をここに定義
    });

    return (
        <AppContext.Provider value={{ state, setState }}>
            {children}
        </AppContext.Provider>
    );
};

export default AppContextProvider;
"""
        },
        "App.js": """import React from 'react';
import { BrowserRouter as Router } from 'react-router-dom';
import AppRoutes from './routes/AppRoutes.jsx';
import AppContextProvider from './context/AppContext.js';

const App = () => {
    return (
        <AppContextProvider>
            <Router>
                <AppRoutes />
            </Router>
        </AppContextProvider>
    );
};

export default App;
""",
        "index.js": """import React from 'react';
import ReactDOM from 'react-dom';
import App from './App.js';
import './index.css';

ReactDOM.render(
    <React.StrictMode>
        <App />
    </React.StrictMode>,
    document.getElementById('root')
);
""",
        "index.css": """body {
    font-family: Arial, sans-serif;
    margin: 0;
    padding: 0;
}

button {
    padding: 10px 20px;
    margin: 20px 0;
    font-size: 16px;
}
"""
    }
}

def create_structure(base_path, structure_dict):
    for name, content in structure_dict.items():
        path = os.path.join(base_path, name)
        if isinstance(content, dict):
            os.makedirs(path, exist_ok=True)
            create_structure(path, content)
        else:
            # ファイルを作成し、内容を書き込む
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Created file: {path}")

def main():
    # プロジェクトディレクトリを作成
    if not os.path.exists(PROJECT_NAME):
        os.makedirs(PROJECT_NAME)
        print(f"Created project directory: {PROJECT_NAME}")
    else:
        print(f"Project directory already exists: {PROJECT_NAME}")

    # ディレクトリ構造とファイルを作成
    create_structure(PROJECT_NAME, structure)

if __name__ == "__main__":
    main()
