// Navigation configuration
const navConfig = {
    screens: {
        LEADERBOARD_NEW: {
            id: 'leaderboard_new',
            title: 'Leaderboard',
            elementId: 'leaderboard',
            isDefault: true,
            onShow: function () {
                buildFreshTable();
                // Ensure default styling for standard leaderboard
                const container = document.getElementById('leaderboard').querySelector('.table-container');
                if (container) {
                    container.classList.remove('extended-table');
                    // Reset inline margin styles that may have been set by extended view
                    container.style.marginLeft = '';
                    container.style.marginRight = '';
                }
            }
        },
        // Add new screen for extended leaderboard
        LEADERBOARD_EXT: {
            id: 'leaderboard_ext',
            title: 'LB (extended)',
            elementId: 'leaderboard', // Reuse the same element
            onShow: function () {
                // If loading for the first time, ensure defaults
                if (this.firstLoad !== true) {
                    this.firstLoad = true;

                    // Reset to defaults if no localStorage data
                    const saved = localStorage.getItem('columnSelection');
                    if (!saved) {
                        // Reset to default columns from tableColumnSets
                        extendedColumnPreferences.selected = tableColumnSets[Screen.LEADERBOARD_EXT]
                            .filter(id => id !== 'rank' && id !== 'player');
                    } else {
                        // Load saved columns
                        tryLoadColumnSelectionFromStorage();
                    }
                }

                buildFreshTable();

                const container = document.getElementById('leaderboard').querySelector('.table-container');
                if (container) {
                    container.classList.add('extended-table');
                    // Apply dynamic width
                    updateExtendedTableWidth();
                }
            }
        },
        COST_ELO: {
            id: 'cost_elo',
            title: 'Cost/Elo',
            elementId: 'cost-elo-view',
            onShow: function () {
                initializeCostEloView();
            }
        },
        HOW_IT_WORKS: {
            id: 'how_it_works',
            title: 'How it works',
            elementId: 'how-it-works'
        },
        NOTES: {
            id: 'notes',
            title: 'Notes',
            elementId: 'considerations',
            onShow: function () {
                // Inject a short blog-style update before rendering markdown
                const el = document.getElementById(this.elementId);
                if (el && !el.__elo_injected) {
                    const intro = document.createElement('div');
                    intro.innerHTML = `
<p><strong>May 2025: Leaderboard overhaul — Elo as the primary metric</strong><br>
We started with a Random Player (<em>chaos monkey</em>) which was surprisingly hard for models to beat. By late 2024, reasoning models began to produce
meaningful games; in April 2025 OpenAI's o3 effectively saturated the original benchmark. We now anchor the leaderboard with Komodo
Dragon (chess engine) skill levels and compute model Elo from combined Random+Dragon games. Random is calibrated vs Dragon first to place random-only
models onto the same scale. Chess remains a test bed for reasoning; Dragon extends the difficulty beyond random. Models that played vs Dragon are marked
with a superscript asterisk in the leaderboard.</p>`;
                    el.prepend(intro);
                    el.__elo_injected = true;
                }
                MinimalMD.render(this.elementId);
            }
        }
    },

    dropdowns: [
        {
            title: 'Leaderboard',
            defaultScreen: 'leaderboard_new',
            items: [
                { title: 'Leaderboard', screen: 'leaderboard_new' },
                { title: 'LB (extended)', screen: 'leaderboard_ext' },
                { title: 'Cost/Elo', screen: 'cost_elo' }
            ]
        }
    ]
};

// Global variable to store parsed CSV data
let parsedCsvData = {
    headers: [],      // CSV headers
    rows: [],         // Array of row objects with parsed data
    specialRows: [],  // Special rows like Stockfish, Random Players
    normalRows: []    // Regular model rows
};
function headerIndex(name) {
    if (!parsedCsvData || !Array.isArray(parsedCsvData.headers)) return -1;
    return parsedCsvData.headers.indexOf(name);
}

function getModelMetadata(player) {
    const fallback = {
        mode_family: player,
        reasoning_level: 'unknown'
    };
    if (typeof modelMetadata === 'undefined' || !modelMetadata || !modelMetadata.models) {
        return fallback;
    }

    const canonicalName = (modelMetadata.aliases && modelMetadata.aliases[player]) || player;
    return modelMetadata.models[canonicalName] || fallback;
}


const Screen = {
    LEADERBOARD_NEW: 'leaderboard_new',
    LEADERBOARD_EXT: 'leaderboard_ext',
    COST_ELO: 'cost_elo',
    HOW_IT_WORKS: 'how_it_works',
    NOTES: 'notes'
};

// Special rows removed from display
const SPECIAL_ROWS = {};

let sortOrderState = {
    [Screen.LEADERBOARD_NEW]: {},
    [Screen.LEADERBOARD_EXT]: {},
};

// Track current sort column for persistence
let currentSortState = {
    [Screen.LEADERBOARD_NEW]: { columnIndex: null, order: null },
    [Screen.LEADERBOARD_EXT]: { columnIndex: null, order: null },
};

let currentScreen = null;
let allRows = []; // Will store row objects for sorting/drawing
let costEloExpanded = false;
let costEloRenderTimer = null;

const csvIndices = {
    player: 0,
    total_games: 2,
    player_wins: 3,
    opponent_wins: 4,
    draws: 5,
    player_wins_percent: 6,
    player_draws_percent: 7,
    average_moves: 8,
    moe_average_moves: 9,
    total_moves: 10,
    player_wrong_actions: 11,
    player_wrong_moves: 12,
    wrong_actions_per_1000moves: 13,
    wrong_moves_per_1000moves: 14,
    mistakes_per_1000moves: 15,
    moe_mistakes_per_1000moves: 16,
    player_avg_material: 17,
    opponent_avg_material: 18,
    material_diff_player_llm_minus_opponent: 19,
    moe_material_diff_llm_minus_rand: 20,
    completion_tokens_black_per_move: 21,
    moe_completion_tokens_black_per_move: 22,
    moe_black_llm_win_rate: 23,
    moe_draw_rate: 24,
    moe_black_llm_loss_rate: 25,
    win_loss: 26,
    moe_win_loss: 27,
    win_loss_non_interrupted: 28,
    moe_win_loss_non_interrupted: 29,
    game_duration: 30,
    moe_game_duration: 31,
    games_interrupted: 32,
    games_interrupted_percent: 33,
    moe_games_interrupted: 34,
    games_not_interrupted: 35,
    games_not_interrupted_percent: 36,
    moe_games_not_interrupted: 37,
    average_game_cost: 38,
    moe_average_game_cost: 39,
    price_per_1000_moves: 40,
    moe_price_per_1000_moves: 41,
    elo: 44,
    elo_moe_95: 45,
    games_vs_random: 46,
    games_vs_dragon: 47
};

let nextPrimarySortValue = 0; // Track the next available primarySort value

document.addEventListener('DOMContentLoaded', () => {
    parseCSVData();
    tryLoadSortStateFromStorage();
    createNavigation();
    fetchAndAnimateBoard();
    showDefaultScreen();

    // Initialize markdown rendering
    setTimeout(() => {
        MinimalMD.render('considerations');
    }, 100);

    setTimeout(setupColumnSelector, 500);
});

// Function to parse CSV data
function parseCSVData() {
    if (typeof data === 'undefined') {
        console.error('CSV data not found. Make sure data.js is loaded before script.js');
        return;
    }

    const lines = data.trim().split('\n').filter(line => line.trim() !== '');

    // Parse headers
    parsedCsvData.headers = lines[0].split(',');

    // Parse rows
    let rowObjects = lines.slice(1).map((line, i) => {
        const cols = line.split(',');
        const metadata = getModelMetadata(cols[csvIndices.player] || '');
        return {
            originalIndex: i,
            cols,
            modeFamily: metadata.mode_family,
            reasoningLevel: metadata.reasoning_level
        };
    });

    // Separate special rows and normal rows
    // Inject benchmark rows with Elo only (placed based on Elo)
    const headers = parsedCsvData.headers;
    const eIdx = headers.indexOf('elo');
    if (eIdx >= 0) {
        function makeRow(name, eloStr) {
            const cols = new Array(headers.length).fill('');
            cols[0] = name;
            cols[eIdx] = eloStr;
            const metadata = getModelMetadata(name);
            return {
                originalIndex: -1,
                cols,
                isBenchmark: true,
                modeFamily: metadata.mode_family,
                reasoningLevel: metadata.reasoning_level
            };
        }
        rowObjects = rowObjects.concat([
            makeRow('Magnus Carlsen', '2941.0'),
            makeRow('Class C player', '1500.0'),
            makeRow('Average chess.com player', '618.7')
        ]);
    }

    parsedCsvData.rows = rowObjects;
    parsedCsvData.specialRows = [];
    parsedCsvData.normalRows = rowObjects;

    console.log('CSV data parsed successfully');
}

// Define all possible columns with metadata
const columnDefinitions = {
    rank: {
        id: 'rank',
        title: '#',
        tooltip: 'Rank of the model',
        isNumeric: true,
        removeFromSpecialRows: true,
        getValue: (cols, idx) => '',
        compareFn: (a, b) => a.rank - b.rank
    },
    player: {
        id: 'player',
        title: 'Player',
        tooltip: 'Model playing as black against a Random Player',
        getValue: (cols) => cols[csvIndices.player],
        isNumeric: false,
        compareFn: (a, b) => a.cols[csvIndices.player].localeCompare(b.cols[csvIndices.player])
    },
    elo: {
        id: 'elo',
        title: 'Elo',
        tooltip: 'Estimated Elo with 95% margin (if available).',
        isNumeric: true,
        getValue: (cols) => {
            const eIdx = headerIndex('elo');
            if (eIdx < 0) return '';
            const e = parseFloat(cols[eIdx]);
            if (isNaN(e)) return 'N/A';
            return e.toFixed(1);
        },
        compareFn: (a, b) => {
            const eIdx = headerIndex('elo');
            if (eIdx < 0) return 0;
            const aVal = parseFloat(a.cols[eIdx]);
            const bVal = parseFloat(b.cols[eIdx]);
            if (isNaN(aVal) && isNaN(bVal)) return 0;
            if (isNaN(aVal)) return -1; // NaN last for DESC
            if (isNaN(bVal)) return 1;
            return aVal - bVal;
        }
    },
    winLoss: {
        id: 'winLoss',
        title: 'Win/Loss',
        tooltip: 'Difference between wins and losses as a percentage of total games (0-100%). This is the primary ranking metric that measures BOTH chess skill AND instruction following ability. A model needs to understand chess strategy AND follow game instructions correctly to score well. 50% represents equal wins/losses, higher scores mean more wins than losses.',
        isNumeric: true,
        getValue: (cols) => {
            const val = parseFloat(cols[csvIndices.win_loss]);
            return isNaN(val) ? "N/A" : (val * 100).toFixed(2) + '%';
        },
        compareFn: (a, b) => {
            const aVal = parseFloat(a.cols[csvIndices.win_loss]) || 0;
            const bVal = parseFloat(b.cols[csvIndices.win_loss]) || 0;
            return aVal - bVal;
        }
    },
    gameDuration: {
        id: 'gameDuration',
        title: 'Game Duration',
        tooltip: 'Percentage of maximum possible game length completed before termination (0-100%). This specifically measures instruction following reliability across many moves. 100% indicates the model either reached a natural conclusion (checkmate, stalemate) or the maximum 200 moves without protocol violations. Lower scores show the model struggled to maintain correct communication as the game progressed.',
        isNumeric: true,
        getValue: (cols) => {
            const val = parseFloat(cols[csvIndices.game_duration]);
            return isNaN(val) ? "N/A" : (val * 100).toFixed(2) + '%';
        },
        compareFn: (a, b) => {
            const aVal = parseFloat(a.cols[csvIndices.game_duration]) || 0;
            const bVal = parseFloat(b.cols[csvIndices.game_duration]) || 0;
            return aVal - bVal;
        }
    },
    tokens: {
        id: 'tokens',
        title: 'Tokens',
        tooltip: 'Number of completion tokens generated per move. Demonstrates the model\'s verbosity. Lower token counts may indicate efficiency, while higher counts may show more detailed reasoning OR more garbage generation (depending on the overall rank, reasoning models generate more tokens and score better, weak models can also be verbose yet show poor performance).',
        getValue: (cols) => {
            const value = parseFloat(cols[csvIndices.completion_tokens_black_per_move]);
            if (isNaN(value)) return 'N/A';
            return value > 1000 ? value.toFixed(1) : value.toFixed(2);
        },
        isNumeric: true,
        compareFn: (a, b) => {
            const aVal = parseFloat(a.cols[csvIndices.completion_tokens_black_per_move]) || 0;
            const bVal = parseFloat(b.cols[csvIndices.completion_tokens_black_per_move]) || 0;
            return aVal - bVal;
        }
    },
    costPerGame: {
        id: 'costPerGame',
        title: 'Cost/Game',
        tooltip: 'Estimated cost per game based on token usage and model pricing.',
        getValue: (cols) => {
            const value = parseFloat(cols[csvIndices.average_game_cost]) || 0;
            return `$${value.toFixed(3)}`;
        },
        isNumeric: true,
        compareFn: (a, b) => {
            const aVal = parseFloat(a.cols[csvIndices.average_game_cost]) || 0;
            const bVal = parseFloat(b.cols[csvIndices.average_game_cost]) || 0;
            return aVal - bVal;
        }
    },
    costPerElo: {
        id: 'costPerElo',
        title: 'Cost/Elo',
        tooltip: 'Estimated cost per 1000 Elo points (Cost/Game divided by Elo, then scaled by 1000). Lower is more cost-efficient.',
        getValue: (cols) => {
            const idx = headerIndex('cost_per_1000_elo');
            const tokensVal = parseFloat(cols[csvIndices.completion_tokens_black_per_move]);
            if (isNaN(tokensVal) || tokensVal <= 0) return 'N/A';

            // Prefer backend-provided metric if present
            if (idx >= 0) {
                const value = parseFloat(cols[idx]);
                return isNaN(value) ? 'N/A' : `$${value.toFixed(5)}`;
            }

            // Fallback: derive from existing columns
            const eloVal = parseFloat(cols[csvIndices.elo]);
            const avgCostVal = parseFloat(cols[csvIndices.average_game_cost]);
            if (isNaN(eloVal) || eloVal <= 0 || isNaN(avgCostVal)) return 'N/A';

            const derived = (avgCostVal / eloVal) * 1000.0;
            return isFinite(derived) ? `$${derived.toFixed(5)}` : 'N/A';
        },
        isNumeric: true,
        compareFn: (a, b) => {
            const idx = headerIndex('cost_per_1000_elo');

            const getVal = (rowCols) => {
                const tokensVal = parseFloat(rowCols[csvIndices.completion_tokens_black_per_move]);
                if (isNaN(tokensVal) || tokensVal <= 0) return Infinity;
                if (idx >= 0) {
                    const v = parseFloat(rowCols[idx]);
                    return isNaN(v) ? Infinity : v;
                }
                const eloVal = parseFloat(rowCols[csvIndices.elo]);
                const avgCostVal = parseFloat(rowCols[csvIndices.average_game_cost]);
                if (isNaN(eloVal) || eloVal <= 0 || isNaN(avgCostVal)) return Infinity;
                const derived = (avgCostVal / eloVal) * 1000.0;
                return isFinite(derived) ? derived : Infinity;
            };

            return getVal(a.cols) - getVal(b.cols);
        }
    },
    avgMoves: {
        id: 'avgMoves',
        title: 'Avg Moves',
        tooltip: 'Average number of moves per game. Shows how many moves were played on average before the game ended.',
        getValue: (cols) => {
            const value = parseFloat(cols[csvIndices.average_moves]) || 0;
            return value.toFixed(2);
        },
        isNumeric: true,
        compareFn: (a, b) => {
            const aVal = parseFloat(a.cols[csvIndices.average_moves]) || 0;
            const bVal = parseFloat(b.cols[csvIndices.average_moves]) || 0;
            return aVal - bVal;
        }
    },
    totalGames: {
        id: 'totalGames',
        title: 'Total Games',
        tooltip: 'Total number of games played by this model.',
        getValue: (cols) => cols[csvIndices.total_games],
        isNumeric: true,
        compareFn: (a, b) => {
            const aVal = parseInt(a.cols[csvIndices.total_games]) || 0;
            const bVal = parseInt(b.cols[csvIndices.total_games]) || 0;
            return aVal - bVal;
        }
    },
    wins: {
        id: 'wins',
        title: 'Wins',
        tooltip: 'Number of games won by the model.',
        getValue: (cols) => cols[csvIndices.player_wins],
        isNumeric: true,
        compareFn: (a, b) => {
            const aVal = parseInt(a.cols[csvIndices.player_wins]) || 0;
            const bVal = parseInt(b.cols[csvIndices.player_wins]) || 0;
            return aVal - bVal;
        }
    },
    losses: {
        id: 'losses',
        title: 'Losses',
        tooltip: 'Number of games lost by the model.',
        getValue: (cols) => cols[csvIndices.opponent_wins],
        isNumeric: true,
        compareFn: (a, b) => {
            const aVal = parseInt(a.cols[csvIndices.opponent_wins]) || 0;
            const bVal = parseInt(b.cols[csvIndices.opponent_wins]) || 0;
            return aVal - bVal;
        }
    },
    draws: {
        id: 'draws',
        title: 'Draws',
        tooltip: 'Number of games that ended in a draw.',
        getValue: (cols) => cols[csvIndices.draws],
        isNumeric: true,
        compareFn: (a, b) => {
            const aVal = parseInt(a.cols[csvIndices.draws]) || 0;
            const bVal = parseInt(b.cols[csvIndices.draws]) || 0;
            return aVal - bVal;
        }
    },
    mistakesPerMove: {
        id: 'mistakesPerMove',
        title: 'Mistakes/1K',
        tooltip: 'Number of mistakes per 1000 moves (e.g. haluscinating a move ort replying with uncrecognized action). Lower is better.',
        getValue: (cols) => {
            const value = parseFloat(cols[csvIndices.mistakes_per_1000moves]) || 0;
            return value.toFixed(2);
        },
        isNumeric: true,
        compareFn: (a, b) => {
            const aVal = parseFloat(a.cols[csvIndices.mistakes_per_1000moves]) || 0;
            const bVal = parseFloat(b.cols[csvIndices.mistakes_per_1000moves]) || 0;
            return aVal - bVal;
        }
    },
    materialDiff: {
        id: 'materialDiff',
        title: 'Material Diff',
        tooltip: 'Average material difference (LLM minus opponent). Higher values indicate the model kept more pieces on the board.',
        getValue: (cols) => {
            const value = parseFloat(cols[csvIndices.material_diff_player_llm_minus_opponent]) || 0;
            return value.toFixed(2);
        },
        isNumeric: true,
        compareFn: (a, b) => {
            const aVal = parseFloat(a.cols[csvIndices.material_diff_player_llm_minus_opponent]) || 0;
            const bVal = parseFloat(b.cols[csvIndices.material_diff_player_llm_minus_opponent]) || 0;
            return aVal - bVal;
        }
    },
    gamesInterrupted: {
        id: 'gamesInterrupted',
        title: 'Games Interrupted',
        tooltip: 'Percentage of games that were interrupted before completion due to LLM failing to make a move or abide by the instructions.',
        getValue: (cols) => {
            const value = parseFloat(cols[csvIndices.games_interrupted_percent]) || 0;
            return (value).toFixed(2) + '%';
        },
        isNumeric: true,
        compareFn: (a, b) => {
            const aVal = parseFloat(a.cols[csvIndices.games_interrupted_percent]) || 0;
            const bVal = parseFloat(b.cols[csvIndices.games_interrupted_percent]) || 0;
            return aVal - bVal;
        }
    }
};

// Define default columns for each table
const tableColumnSets = {
    [Screen.LEADERBOARD_NEW]: ['rank', 'player', 'elo', 'gameDuration', 'tokens', 'costPerGame'],
    [Screen.LEADERBOARD_EXT]: ['rank', 'player', 'elo', 'winLoss', 'gameDuration', 'tokens', 'costPerGame', 'avgMoves']
};

// Define column preferences for extended table (will be loaded from localStorage)
const EXTENDED_LB_VERSION = 'v3';
let extendedColumnPreferences = {
    available: Object.keys(columnDefinitions).filter(id => id !== 'rank' && id !== 'player'),
    selected: tableColumnSets[Screen.LEADERBOARD_EXT].filter(id => id !== 'rank' && id !== 'player'),
    maxColumns: 7
};

// Default sort functions
const defaultSortFunctions = {
    [Screen.LEADERBOARD_NEW]: (colsA, colsB) => {
        const eIdx = headerIndex('elo');
        const eloA = eIdx >= 0 ? parseFloat(colsA[eIdx]) : NaN;
        const eloB = eIdx >= 0 ? parseFloat(colsB[eIdx]) : NaN;
        const gdA = parseFloat(colsA[csvIndices.game_duration]) || 0;
        const gdB = parseFloat(colsB[csvIndices.game_duration]) || 0;
        const tokA = parseFloat(colsA[csvIndices.completion_tokens_black_per_move]) || 0;
        const tokB = parseFloat(colsB[csvIndices.completion_tokens_black_per_move]) || 0;
        // Primary: Elo DESC (NaNs last). Then Game Duration DESC, Tokens ASC
        if (eIdx >= 0 && (!isNaN(eloA) || !isNaN(eloB))) {
            if (isNaN(eloA)) return 1;
            if (isNaN(eloB)) return -1;
            if (eloB !== eloA) return eloB - eloA;
        }
        return (gdB - gdA) || (tokA - tokB);
    },
    [Screen.LEADERBOARD_EXT]: (colsA, colsB) => {
        const eIdx = headerIndex('elo');
        const eloA = eIdx >= 0 ? parseFloat(colsA[eIdx]) : NaN;
        const eloB = eIdx >= 0 ? parseFloat(colsB[eIdx]) : NaN;
        const wlA = parseFloat(colsA[csvIndices.win_loss]) || 0;
        const wlB = parseFloat(colsB[csvIndices.win_loss]) || 0;
        const gdA = parseFloat(colsA[csvIndices.game_duration]) || 0;
        const gdB = parseFloat(colsB[csvIndices.game_duration]) || 0;
        const tokA = parseFloat(colsA[csvIndices.completion_tokens_black_per_move]) || 0;
        const tokB = parseFloat(colsB[csvIndices.completion_tokens_black_per_move]) || 0;
        const costA = parseFloat(colsA[csvIndices.average_game_cost]) || 0;
        const costB = parseFloat(colsB[csvIndices.average_game_cost]) || 0;

        // Primary: Elo DESC (NaNs last)
        if (eIdx >= 0 && (!isNaN(eloA) || !isNaN(eloB))) {
            if (isNaN(eloA)) return 1;
            if (isNaN(eloB)) return -1;
            if (eloB !== eloA) return eloB - eloA;
        }

        // Then Win/Loss DESC, Game Duration DESC, Tokens ASC, Cost ASC
        return (wlB - wlA) || (gdB - gdA) || (tokA - tokB) || (costA - costB);
    }
};

// Helper to get active columns for the current screen
function getActiveColumns() {
    if (currentScreen === Screen.LEADERBOARD_EXT) {
        // For extended view, use the selected columns from preferences
        const selectedIds = ['rank', 'player', ...extendedColumnPreferences.selected];
        return selectedIds.map(id => columnDefinitions[id]);
    } else {
        // For other views, use the predefined column sets
        return (tableColumnSets[currentScreen] || []).map(id => columnDefinitions[id]);
    }
}

function collapseCostEloOverlay() {
    costEloExpanded = false;
    document.body.classList.remove('cost-elo-expanded-open');
    const container = document.querySelector('.cost-elo-container');
    if (container) container.classList.remove('cost-elo-expanded');
    const button = document.getElementById('cost-elo-expand');
    if (button) {
        button.setAttribute('aria-expanded', 'false');
        button.textContent = 'Expand';
    }
}

function cleanupCostEloView() {
    if (costEloRenderTimer !== null) {
        clearTimeout(costEloRenderTimer);
        costEloRenderTimer = null;
    }
    collapseCostEloOverlay();
    const tooltip = document.getElementById('cost-elo-tooltip');
    if (tooltip) tooltip.remove();
    const canvas = document.getElementById('cost-elo-chart');
    if (canvas) {
        canvas.onmousemove = null;
        canvas.onmouseleave = null;
    }
}

function showPane(screenId) {
    const scrollPos = window.scrollY;
    const screenConfig = Object.values(navConfig.screens).find(s => s.id === screenId);

    if (!screenConfig) {
        console.error(`Screen ${screenId} not found in configuration`);
        return;
    }

    if (currentScreen === Screen.COST_ELO && screenId !== Screen.COST_ELO) {
        cleanupCostEloView();
    }
    hidePopup();

    // Ensure CSV data is parsed if not already done
    if (parsedCsvData.rows.length === 0) {
        parseCSVData();
    }

    currentScreen = screenId;

    // Hide all panes first to reset state if elementId is reused
    Object.values(navConfig.screens).forEach(screen => {
        const element = document.getElementById(screen.elementId);
        if (element) {
            element.style.display = 'none';
            // Remove extended class if present
            const container = element.querySelector('.table-container');
            if (container) {
                container.classList.remove('extended-table');
            }
        }
    });

    // Show the selected pane
    const selectedElement = document.getElementById(screenConfig.elementId);
    if (selectedElement) selectedElement.style.display = 'block';

    // Update button states - add null checks
    document.querySelectorAll('.button-container button').forEach(button => {
        if (button) button.classList.remove('selected');
    });

    // Find the button/dropdown corresponding to the screenId
    const parentDropdown = navConfig.dropdowns.find(dropdown =>
        dropdown.defaultScreen === screenId ||
        (dropdown.items && dropdown.items.some(item => item.screen === screenId))
    );

    if (parentDropdown) {
        const dropbtn = document.querySelector('.dropbtn');
        if (dropbtn) dropbtn.classList.add('selected');

        if (parentDropdown.items && parentDropdown.items.length > 0) {
            const item = parentDropdown.items.find(item => item.screen === screenId);
            if (item) {
                const dropbtn = document.querySelector('.dropbtn');
                if (dropbtn) {
                    // Keep the arrow when updating button text
                    dropbtn.innerHTML = `${item.title} <span class="dropdown-arrow">▼</span>`;
                }
            }
        }
    } else {
        const button = Array.from(document.querySelectorAll('.button-container button'))
            .find(btn => btn && btn.textContent === screenConfig.title);
        if (button) button.classList.add('selected');
    }

    // Run onShow handler if defined
    if (screenConfig.onShow && typeof screenConfig.onShow === 'function') {
        screenConfig.onShow.call(screenConfig);
    }

    // Setup column selector after pane is shown
    setupColumnSelector();

    // Restore scroll position
    window.scrollTo(0, scrollPos);

    // Analytics
    if (typeof gtag === 'function') {
        gtag('event', 'page_view', {
            'page_title': document.title + ' - ' + screenId,
            'page_path': '/' + screenId
        });
    }
}

function fetchAndAnimateBoard() {
    fetch('moves.txt')
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.text();
        })
        .then(data => {
            const boardStates = data.trim().split('-\n');
            let currentIndex = 0;

            let interval = 1000; // Initial interval in milliseconds
            let resetGameInterval = 7000;

            function animateBoard() {
                document.querySelector('pre.board').textContent = boardStates[currentIndex].trim();
                document.querySelector('div.game-over').style.display = 'none';
                currentIndex = (currentIndex + 1) % boardStates.length;

                if (currentIndex === 0) {
                    document.querySelector('div.game-over').style.display = 'block';
                    currentIndex = 0;
                    setTimeout(animateBoard, resetGameInterval);
                } else {
                    // Decrease the interval progressively
                    interval = Math.max(50, interval - 25); // Decrease by 25ms, but not less than 50ms
                    setTimeout(animateBoard, interval);
                }
            }

            animateBoard(); // Start the animation
        })
        .catch(error => {
            console.error('Error fetching moves.txt:', error);
        });
}

function showPlayerDetailsPopup(row, columns) {
    const popup = document.getElementById('popup');
    const totalGames = columns[csvIndices.total_games];

    const wins = columns[csvIndices.player_wins];
    const losses = columns[csvIndices.opponent_wins];
    const draws = columns[csvIndices.draws];

    const winLoss = columns[csvIndices.win_loss];
    const moeWinLoss = columns[csvIndices.moe_win_loss];
    const gameDuration = columns[csvIndices.game_duration];
    const moeGameDuration = columns[csvIndices.moe_game_duration];

    const gamesInterrupted = columns[csvIndices.games_interrupted];
    const gamesInterruptedPercent = columns[csvIndices.games_interrupted_percent];
    const moeGamesInterrupted = columns[csvIndices.moe_games_interrupted];

    const moeWins = columns[csvIndices.moe_black_llm_win_rate];
    const moeLosses = columns[csvIndices.moe_black_llm_loss_rate];
    const moeDraws = columns[csvIndices.moe_draw_rate];

    const averageMoves = columns[csvIndices.average_moves];
    const materialDiff = columns[csvIndices.material_diff_player_llm_minus_opponent];
    const mistakesPer1000Moves = columns[csvIndices.mistakes_per_1000moves];
    const completionTokensBlackPerMove = columns[csvIndices.completion_tokens_black_per_move];

    const moeAverageMoves = columns[csvIndices.moe_average_moves];
    const moeMaterialDiff = columns[csvIndices.moe_material_diff_llm_minus_rand];
    const moeMistakesPer1000Moves = columns[csvIndices.moe_mistakes_per_1000moves];
    const moeCompletionTokensBlackPerMove = columns[csvIndices.moe_completion_tokens_black_per_move];

    // Add cost metrics
    const averageGameCost = columns[csvIndices.average_game_cost];
    const moeAverageGameCost = columns[csvIndices.moe_average_game_cost];
    const pricePer1000Moves = columns[csvIndices.price_per_1000_moves];
    const moePricePer1000Moves = columns[csvIndices.moe_price_per_1000_moves];

    // Elo in popup (robust to missing columns)
    const eIdx = headerIndex('elo');
    const mIdx = headerIndex('elo_moe_95');
    const rIdx = headerIndex('games_vs_random');
    const dIdx = headerIndex('games_vs_dragon');
    const elo = eIdx >= 0 ? parseFloat(columns[eIdx]) : NaN;
    const eloMoe = mIdx >= 0 ? parseFloat(columns[mIdx]) : NaN;
    const eloDisplay = isNaN(elo) ? 'N/A' : elo.toFixed(1);
    const gvr = rIdx >= 0 ? (columns[rIdx] || '0') : '0';
    const gvd = dIdx >= 0 ? (columns[dIdx] || '0') : '0';
    const moeDisplay = (!isNaN(eloMoe) && eloMoe > 0) ? ` ± ${eloMoe.toFixed(1)}` : '';

    document.getElementById('total-games').innerHTML = `<span>Games:</span> ${parseInt(totalGames)} (vsR ${gvr}, vsD ${gvd})`;

    document.getElementById('elo').innerHTML = `<span>Elo:</span> ${eloDisplay}${moeDisplay}`;
    document.getElementById('win_loss').innerHTML =
        `<span>Win/Loss:</span> ${parseFloat(winLoss)} ± ${parseFloat(moeWinLoss)}`;
    document.getElementById('game-duration').innerHTML =
        `<span>Game Duration:</span> ${parseFloat(gameDuration).toFixed(3)} ± ${parseFloat(moeGameDuration).toFixed(3)}`;
    document.getElementById('games-interrupted').innerHTML =
        `<span>Games Intptd:</span> ${parseInt(gamesInterrupted)} (${parseFloat(gamesInterruptedPercent / 100).toFixed(3)} ± ${parseFloat(moeGamesInterrupted).toFixed(3)})`;
    document.getElementById('wins').innerHTML =
        `<span>Wins:</span> ${parseInt(wins)} (` +
        `${((parseInt(wins) / parseInt(totalGames))).toFixed(3)} ± ${parseFloat(moeWins).toFixed(3)})`;
    document.getElementById('losses').innerHTML =
        `<span>Losses:</span> ${parseInt(losses)} (` +
        `${((parseInt(losses) / parseInt(totalGames))).toFixed(2)} ± ${parseFloat(moeLosses).toFixed(3)})`;
    document.getElementById('draws').innerHTML =
        `<span>Draws:</span> ${parseInt(draws)} (` +
        `${((parseInt(draws) / parseInt(totalGames))).toFixed(3)} ± ${parseFloat(moeDraws).toFixed(3)})`;
    document.getElementById('average-moves').innerHTML = `<span>Average Moves:</span> ${parseFloat(averageMoves).toFixed(2)} ± ${parseFloat(moeAverageMoves).toFixed(2)}`;
    document.getElementById('material-diff').innerHTML = `<span>Material Diff:</span> ${parseFloat(materialDiff).toFixed(2)} ± ${parseFloat(moeMaterialDiff).toFixed(2)}`;
    document.getElementById('mistakes-per-1000moves').innerHTML = `<span>Mistakes/1k_Moves:</span> ${parseFloat(mistakesPer1000Moves).toFixed(2)} ± ${parseFloat(moeMistakesPer1000Moves).toFixed(2)}`;
    document.getElementById('completion-tokens-black-per-move').innerHTML = `<span>Compl.Toks/Move:</span> ${parseFloat(completionTokensBlackPerMove).toFixed(2)} ± ${parseFloat(moeCompletionTokensBlackPerMove).toFixed(2)}`;

    // Add cost information to popup
    document.getElementById('cost-per-game').innerHTML = `<span>Cost/Game:</span> $${parseFloat(averageGameCost).toFixed(4)} ± $${parseFloat(moeAverageGameCost).toFixed(4)}`;

    const costPer100MovesEl = document.getElementById('cost-per-100-moves');
    if (costPer100MovesEl) {
        const costPer100MovesVal = parseFloat(pricePer1000Moves) / 10;
        const moeCostPer100MovesVal = parseFloat(moePricePer1000Moves) / 10;
        if (isNaN(costPer100MovesVal) || isNaN(moeCostPer100MovesVal)) {
            costPer100MovesEl.innerHTML = `<span>Cost/100 Moves:</span> N/A`;
        } else {
            costPer100MovesEl.innerHTML = `<span>Cost/100 Moves:</span> $${costPer100MovesVal.toFixed(4)} ± $${moeCostPer100MovesVal.toFixed(4)}`;
        }
    }

    const costPerEloEl = document.getElementById('cost-per-elo');
    if (costPerEloEl) {
        const idxCostPerElo = headerIndex('cost_per_1000_elo');
        const idxMoeCostPerElo = headerIndex('moe_cost_per_1000_elo');

        let costPerEloVal = idxCostPerElo >= 0 ? parseFloat(columns[idxCostPerElo]) : NaN;
        let moeCostPerEloVal = idxMoeCostPerElo >= 0 ? parseFloat(columns[idxMoeCostPerElo]) : NaN;

        // N/A when tokens are zero.
        if (isNaN(parseFloat(completionTokensBlackPerMove)) || parseFloat(completionTokensBlackPerMove) <= 0) {
            costPerEloVal = NaN;
            moeCostPerEloVal = NaN;
        }

        // Fallback: derive if backend column is absent or incomplete
        if (isNaN(costPerEloVal) || isNaN(moeCostPerEloVal)) {
            if (!isNaN(elo) && elo > 0 && !isNaN(parseFloat(completionTokensBlackPerMove)) && parseFloat(completionTokensBlackPerMove) > 0) {
                const costVal = parseFloat(averageGameCost) || 0;
                const moeCostVal = parseFloat(moeAverageGameCost) || 0;

                const term1 = moeCostVal / elo;
                const term2 = (isNaN(eloMoe) ? 0 : (costVal * eloMoe) / (elo * elo));

                costPerEloVal = (costVal / elo) * 1000.0;
                moeCostPerEloVal = 1000.0 * Math.sqrt(term1 * term1 + term2 * term2);
            }
        }

        if (isNaN(costPerEloVal) || isNaN(moeCostPerEloVal)) {
            costPerEloEl.innerHTML = `<span>Cost/Elo:</span> N/A`;
        } else {
            costPerEloEl.innerHTML = `<span>Cost/Elo:</span> $${costPerEloVal.toFixed(5)} ± $${moeCostPerEloVal.toFixed(5)}`;
        }
    }

    const rect = row.getBoundingClientRect();
    if (window.innerWidth < 1350) {
        popup.style.top = `${rect.bottom + window.scrollY}px`;
        popup.style.right = `${rect.left + window.scrollX}px`;
        popup.style.left = '';
    }
    else {
        popup.style.top = `${rect.top + window.scrollY}px`;
        popup.style.left = `${rect.right + window.scrollX}px`;
        popup.style.right = '';
    }
    popup.style.display = 'block';
}

function hidePopup() {
    const popup = document.getElementById('popup');
    if (popup) popup.style.display = 'none';
}

// Create navigation elements dynamically
function createNavigation() {
    const buttonContainer = document.querySelector('.button-container');
    if (!buttonContainer) return;

    // Clear existing content
    buttonContainer.innerHTML = '';

    // Create dropdowns first to make them appear on the left
    navConfig.dropdowns.forEach(dropdown => {
        const dropdownContainer = document.createElement('div');
        dropdownContainer.className = 'custom-dropdown';

        const dropbtn = document.createElement('button');
        dropbtn.className = 'dropbtn';

        // If dropdown has items, create dropdown content and add arrow
        if (dropdown.items && dropdown.items.length > 0) {
            dropbtn.innerHTML = `${dropdown.title} <span class="dropdown-arrow">▼</span>`;
            dropbtn.onclick = () => toggleDropdown(dropdownContainer);

            const dropdownContent = document.createElement('div');
            dropdownContent.className = 'dropdown-content';

            dropdown.items.forEach(item => {
                const option = document.createElement('div');
                option.textContent = item.title;
                option.onclick = () => showPane(item.screen);
                dropdownContent.appendChild(option);
            });

            dropdownContainer.appendChild(dropbtn);
            dropdownContainer.appendChild(dropdownContent);
        } else {
            // If no items, just make the button show the default screen
            dropbtn.textContent = dropdown.title;
            dropbtn.onclick = () => showPane(dropdown.defaultScreen);
            dropdownContainer.appendChild(dropbtn);
        }

        buttonContainer.appendChild(dropdownContainer);
    });

    // Create regular buttons after dropdowns
    Object.values(navConfig.screens).forEach(screen => {
        // Skip screens that should be in dropdowns
        if (isScreenInDropdown(screen.id)) return;

        const button = document.createElement('button');
        button.textContent = screen.title;
        button.onclick = () => showPane(screen.id);
        buttonContainer.appendChild(button);
    });
}

function isScreenInDropdown(screenId) {
    for (const dropdown of navConfig.dropdowns) {
        if (dropdown.defaultScreen === screenId) return true;
        if (dropdown.items) {
            for (const item of dropdown.items) {
                if (item.screen === screenId) return true;
            }
        }
    }
    return false;
}

function showDefaultScreen() {
    const defaultScreen = Object.values(navConfig.screens).find(screen => screen.isDefault);
    if (defaultScreen) {
        showPane(defaultScreen.id);
    } else {
        const firstScreen = Object.values(navConfig.screens)[0];
        if (firstScreen) showPane(firstScreen.id);
    }
}

function toggleDropdown(dropdownContainer) {
    const dropdownContent = dropdownContainer.querySelector('.dropdown-content');
    if (dropdownContent) {
        dropdownContent.classList.toggle('show');
    } else {
        const dropdownBtn = dropdownContainer.querySelector('.dropbtn');
        // Extract title text without the arrow
        const buttonText = dropdownBtn ? dropdownBtn.textContent.replace('▼', '').trim() : '';

        const dropdownConfig = navConfig.dropdowns.find(d =>
            d.title === buttonText);
        if (dropdownConfig) {
            showPane(dropdownConfig.defaultScreen);
        }
    }
}

// Close the dropdown if clicked outside
window.onclick = function (event) {
    if (!event.target.matches('.dropbtn') && !event.target.matches('.dropdown-arrow')) {
        var dropdowns = document.getElementsByClassName('dropdown-content');
        for (var i = 0; i < dropdowns.length; i++) {
            var openDropdown = dropdowns[i];
            if (openDropdown && openDropdown.classList.contains('show')) {
                openDropdown.classList.remove('show');
            }
        }
    }
}

function toggleSnippet(button) {
    const snippet = button.nextElementSibling; // Get the <pre> element
    if (snippet.style.display === "none") {
        snippet.style.display = "block";
        button.textContent = "Hide Snippet";
    } else {
        snippet.style.display = "none";
        button.textContent = "Show Snippet";
    }
}

function sortTable(columnIndex = null, newOrder = null) {
    const sortOrderObj = sortOrderState[currentScreen];
    const activeColumns = getActiveColumns();

    // Guard against stale saved sort indexes when the column set changes.
    if (columnIndex !== null && (!activeColumns[columnIndex] || columnIndex < 0)) {
        columnIndex = null;
        newOrder = null;
    }

    // If columnIndex is provided, handle sort order toggling
    if (columnIndex !== null) {
        const currentOrder = sortOrderObj[columnIndex] || 'asc';
        newOrder = newOrder || (currentOrder === 'asc' ? 'desc' : 'asc');
        sortOrderObj[columnIndex] = newOrder;

        // Save sort state to localStorage
        currentSortState[currentScreen] = { columnIndex, order: newOrder };
        saveSortStateToStorage();
    }

    // Remove special rows (Random/Stockfish) from display
    const bottomRows = [];

    // Filter out special rows and separate fixed vs unfixed
    const normalRows = allRows.filter(row => {
        const playerName = row.cols[csvIndices.player];
        return !Object.values(SPECIAL_ROWS).includes(playerName);
    });

    const fixedRows = normalRows.filter(row =>
        row.primarySort !== undefined && row.primarySort < 9999);
    const unfixedRows = normalRows.filter(row =>
        row.primarySort === undefined || row.primarySort === 9999);

    // Sort unfixed rows according to current criteria
    unfixedRows.sort((a, b) => {
        if (columnIndex === null) {
            return defaultSortFunctions[currentScreen](a.cols, b.cols);
        } else {
            const col = activeColumns[columnIndex];
            if (col.compareFn) {
                const res = col.compareFn(a, b);
                if (col.title === '#') {
                    return res;
                }
                return newOrder === 'asc' ? res : -res;
            } else {
                const aText = a.cols[columnIndex].trim();
                const bText = b.cols[columnIndex].trim();
                const comparison = col.isNumeric
                    ? parseFloat(aText) - parseFloat(bText)
                    : aText.localeCompare(bText);
                return newOrder === 'asc' ? comparison : -comparison;
            }
        }
    });

    // Sort fixed rows by primarySort
    fixedRows.sort((a, b) => a.primarySort - b.primarySort);

    // Combine fixed and unfixed rows (no special rows)
    allRows = [...fixedRows, ...unfixedRows];

    // Render the table
    renderTable();

    // Update sort indicators
    if (columnIndex !== null) {
        document.querySelectorAll('#leaderboard th').forEach(headerCell => {
            const cleanText = headerCell.textContent.replace(/[▲▼]/g, '').trim();
            headerCell.innerHTML = `${cleanText}&nbsp;&nbsp;`;
        });

        const sortedHeaderCell = document.querySelectorAll('#leaderboard th')[columnIndex];
        if (sortedHeaderCell) {
            const baseText = sortedHeaderCell.textContent.replace(/[▲▼]/g, '').trim();
            const indicator = sortOrderObj[columnIndex] === 'asc' ? '▲' : '▼';
            sortedHeaderCell.innerHTML = `${baseText}${indicator ? '&nbsp;' + indicator : '&nbsp;&nbsp;'}`;
        }
    }
}

function renderTable() {
    const tbody = document.querySelector('#leaderboard tbody');
    tbody.innerHTML = '';
    const activeColumns = getActiveColumns();

    allRows.forEach((row, idx) => {
        const tr = document.createElement('tr');
        const isBottomRow = false;

        // Add 'fixed' class to rows with primarySort < 9999
        if (row.primarySort !== undefined && row.primarySort < 9999) {
            tr.classList.add('fixed');
        }

        // Benchmarks styled differently
        if (row.isBenchmark) {
            tr.classList.add('benchmark');
        }

        activeColumns.forEach((col) => {
            let cellValue;
            if (col.removeFromSpecialRows && isBottomRow) {
                cellValue = '';
            } else if (col.id === 'rank') {
                // Always use the original rank (assigned once during buildFreshTable)
                const base = row.rank || '';
                // Superscript star for models that have Dragon games
                const gvdIdx = headerIndex('games_vs_dragon');
                const gvd = gvdIdx >= 0 ? parseInt(row.cols[gvdIdx] || '0') : (parseInt((row.cols[csvIndices.games_vs_dragon] || '0')) || 0);
                const label = (!isNaN(gvd) && gvd > 0) ? `${base}<sup>*</sup>` : `${base}`;
                const td = document.createElement('td');
                td.innerHTML = label;
                tr.appendChild(td);
                return;
            } else {
                cellValue = col.getValue(row.cols, idx);
            }
            const td = document.createElement('td');
            td.textContent = cellValue;
            tr.appendChild(td);
        });

        // Add event listeners
        tr.addEventListener('mouseenter', () => showPlayerDetailsPopup(tr, row.cols));
        tr.addEventListener('mouseleave', hidePopup);
        tr.addEventListener('dblclick', (e) => {
            e.preventDefault();
            toggleRowFixed(row);
        });
        tr.addEventListener('click', () => {
            showPlayerDetailsPopup(tr, row.cols);
        });

        tbody.appendChild(tr);
    });
}

function toggleRowFixed(row) {
    const isBottomRow = false;

    // Skip special rows
    if (isBottomRow) return;

    // Function to recalculate primarySort values to ensure they're sequential
    function recalculatePrimarySortValues() {
        // Get all fixed rows
        const fixedRows = allRows.filter(row =>
            row.primarySort !== undefined && row.primarySort < 9999
        ).sort((a, b) => a.primarySort - b.primarySort);

        // Reassign primarySort values sequentially
        fixedRows.forEach((row, index) => {
            row.primarySort = index;
        });

        // Update nextPrimarySortValue
        nextPrimarySortValue = fixedRows.length;
    }

    // If row is already fixed, unfix it
    if (row.primarySort !== undefined && row.primarySort < 9999) {
        row.primarySort = 9999;

        // Recalculate all primarySort values to ensure they're sequential
        recalculatePrimarySortValues();
    } else {
        // Fix the row at the top with the next available primarySort value
        row.primarySort = nextPrimarySortValue++;

        // Store original rank if not already set
        if (row.originalRank === undefined) {
            row.originalRank = row.rank;
        }
    }

    // Use sortTable to re-sort the rows
    sortTable();
}

// Update setupColumnSelector to use the new column definitions
function setupColumnSelector() {
    const btn = document.getElementById('column-selector-btn');
    const dropdown = document.getElementById('column-selector-dropdown');
    const optionsContainer = document.getElementById('column-options');

    if (!btn || !dropdown || !optionsContainer) return;

    // Column selector is shown/hidden via CSS based on .extended-table class now
    if (currentScreen !== Screen.LEADERBOARD_EXT) {
        dropdown.classList.remove('show');
        return;
    }

    // Toggle dropdown visibility
    btn.onclick = function (event) {
        event.stopPropagation();
        dropdown.classList.toggle('show');

        // If opening the dropdown, initialize options
        if (dropdown.classList.contains('show')) {
            populateColumnOptions();
        }
    };

    // Bind dismissal handlers once; setupColumnSelector runs on every navigation.
    if (!window.__columnSelectorDismissBound) {
        window.__columnSelectorDismissBound = true;
        window.addEventListener('click', function (event) {
            const currentDropdown = document.getElementById('column-selector-dropdown');
            const currentButton = document.getElementById('column-selector-btn');
            if (currentDropdown && currentButton &&
                !currentDropdown.contains(event.target) && event.target !== currentButton) {
                currentDropdown.classList.remove('show');
            }
        });
        document.addEventListener('keydown', function (event) {
            const currentDropdown = document.getElementById('column-selector-dropdown');
            if (event.key === 'Escape' && currentDropdown) {
                currentDropdown.classList.remove('show');
            }
        });
    }
}

function populateColumnOptions() {
    const optionsContainer = document.getElementById('column-options');
    if (!optionsContainer) return;

    // Clear existing options
    optionsContainer.innerHTML = '';

    // Create checkbox for each available column
    extendedColumnPreferences.available.forEach(columnId => {
        const column = columnDefinitions[columnId];
        if (!column) return;

        const option = document.createElement('div');
        option.className = 'column-option';

        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.id = 'col-' + columnId;
        checkbox.checked = extendedColumnPreferences.selected.includes(columnId);
        checkbox.disabled = !checkbox.checked &&
            extendedColumnPreferences.selected.length >= extendedColumnPreferences.maxColumns;

        const label = document.createElement('label');
        label.htmlFor = 'col-' + columnId;
        label.textContent = column.title;

        // Handle checkbox change
        checkbox.onchange = function () {
            if (this.checked) {
                // Add column if not already selected and under max limit
                if (!extendedColumnPreferences.selected.includes(columnId) &&
                    extendedColumnPreferences.selected.length < extendedColumnPreferences.maxColumns) {
                    extendedColumnPreferences.selected.push(columnId);
                }
            } else {
                // Remove column if selected
                const index = extendedColumnPreferences.selected.indexOf(columnId);
                if (index !== -1) {
                    extendedColumnPreferences.selected.splice(index, 1);
                }
            }

            // Update checkbox states based on selection
            updateCheckboxStates();

            // Save to localStorage
            saveColumnSelectionToStorage();

            // Rebuild table with new column selection
            buildFreshTable();

            // Update table width based on selected columns
            updateExtendedTableWidth();
        };

        option.appendChild(checkbox);
        option.appendChild(label);
        optionsContainer.appendChild(option);
    });
}

function updateCheckboxStates() {
    const maxReached = extendedColumnPreferences.selected.length >= extendedColumnPreferences.maxColumns;

    // Update all checkboxes
    extendedColumnPreferences.available.forEach(columnId => {
        const checkbox = document.getElementById('col-' + columnId);
        if (checkbox) {
            // Disable unchecked boxes if max is reached
            checkbox.disabled = !checkbox.checked && maxReached;
        }
    });
}

function saveColumnSelectionToStorage() {
    try {
        localStorage.setItem('columnSelection', JSON.stringify({
            version: EXTENDED_LB_VERSION,
            columns: extendedColumnPreferences.selected
        }));
    } catch (e) {
        console.error('Failed to save column selection to localStorage:', e);
    }
}

function tryLoadColumnSelectionFromStorage() {
    try {
        const saved = localStorage.getItem('columnSelection');
        if (saved) {
            const parsed = JSON.parse(saved);

            // Check version - reset to defaults if version mismatch or missing
            if (!parsed.version || parsed.version !== EXTENDED_LB_VERSION) {
                console.log('Column selection version mismatch, resetting to defaults');
                extendedColumnPreferences.selected = tableColumnSets[Screen.LEADERBOARD_EXT]
                    .filter(id => id !== 'rank' && id !== 'player');
                saveColumnSelectionToStorage();
                return;
            }

            // Handle both old format (array) and new format (object with columns)
            const savedSelection = Array.isArray(parsed) ? parsed : (parsed.columns || []);

            // Validate saved selection
            const validSelection = savedSelection.filter(id =>
                extendedColumnPreferences.available.includes(id)
            );

            // Only use valid selection if not empty and within limits
            if (validSelection.length > 0 && validSelection.length <= extendedColumnPreferences.maxColumns) {
                extendedColumnPreferences.selected = validSelection;
            } else {
                // If saved selection is invalid, reset to defaults
                extendedColumnPreferences.selected = tableColumnSets[Screen.LEADERBOARD_EXT]
                    .filter(id => id !== 'rank' && id !== 'player');

                // Save correct defaults back to localStorage
                saveColumnSelectionToStorage();
            }

            // Update table width if we're in extended view
            if (currentScreen === Screen.LEADERBOARD_EXT) {
                updateExtendedTableWidth();
            }
        }
    } catch (e) {
        console.error('Failed to load column selection from localStorage:', e);
        // Reset to defaults on error
        extendedColumnPreferences.selected = tableColumnSets[Screen.LEADERBOARD_EXT]
            .filter(id => id !== 'rank' && id !== 'player');
    }
}

function saveSortStateToStorage() {
    try {
        localStorage.setItem('sortState', JSON.stringify({
            version: EXTENDED_LB_VERSION,
            state: currentSortState
        }));
    } catch (e) {
        console.error('Failed to save sort state to localStorage:', e);
    }
}

function tryLoadSortStateFromStorage() {
    try {
        const saved = localStorage.getItem('sortState');
        if (saved) {
            const parsed = JSON.parse(saved);

            // Check version
            if (!parsed.version || parsed.version !== EXTENDED_LB_VERSION) {
                console.log('Sort state version mismatch, using defaults');
                return;
            }

            if (parsed.state) {
                // Restore sort state
                if (parsed.state[Screen.LEADERBOARD_NEW]) {
                    currentSortState[Screen.LEADERBOARD_NEW] = parsed.state[Screen.LEADERBOARD_NEW];
                }
                if (parsed.state[Screen.LEADERBOARD_EXT]) {
                    currentSortState[Screen.LEADERBOARD_EXT] = parsed.state[Screen.LEADERBOARD_EXT];
                }
            }
        }
    } catch (e) {
        console.error('Failed to load sort state from localStorage:', e);
    }
}

function setCostEloExpanded(expanded) {
    const container = document.querySelector('.cost-elo-container');
    const button = document.getElementById('cost-elo-expand');
    if (!container || !button) return;

    costEloExpanded = expanded;
    container.classList.toggle('cost-elo-expanded', expanded);
    document.body.classList.toggle('cost-elo-expanded-open', expanded);
    button.setAttribute('aria-expanded', String(expanded));
    button.textContent = expanded ? 'Close' : 'Expand';
    renderCostEloPareto();
}

function initializeCostEloView() {
    const button = document.getElementById('cost-elo-expand');
    if (button && button.dataset.bound !== 'true') {
        button.dataset.bound = 'true';
        button.addEventListener('click', () => setCostEloExpanded(!costEloExpanded));
    }
    if (!window.__costEloEscapeBound) {
        window.__costEloEscapeBound = true;
        window.addEventListener('keydown', event => {
            if (event.key === 'Escape' && costEloExpanded) {
                setCostEloExpanded(false);
            }
        });
    }
    if (costEloRenderTimer !== null) {
        clearTimeout(costEloRenderTimer);
    }
    costEloRenderTimer = setTimeout(() => {
        costEloRenderTimer = null;
        if (currentScreen === Screen.COST_ELO) {
            renderCostEloPareto();
        }
    }, 0);
}

function getCostEloPoints() {
    return parsedCsvData.normalRows
        .filter(row => !row.isBenchmark)
        .map(row => {
            const columns = row.cols;
            const cost = parseFloat(columns[csvIndices.average_game_cost]);
            const elo = parseFloat(columns[csvIndices.elo]);
            if (!Number.isFinite(cost) || cost <= 0 || !Number.isFinite(elo) || elo < 0) {
                return null;
            }

            const pricePer1000Moves = parseFloat(columns[csvIndices.price_per_1000_moves]);
            const costPer100Moves = Number.isFinite(pricePer1000Moves) ? pricePer1000Moves / 10 : NaN;
            const costPerElo = elo > 0 ? (cost / elo) * 1000 : NaN;

            return {
                player: columns[csvIndices.player],
                modeFamily: row.modeFamily || columns[csvIndices.player],
                reasoningLevel: row.reasoningLevel || 'unknown',
                cost,
                costMoe: parseFloat(columns[csvIndices.moe_average_game_cost]),
                costPer100Moves,
                costPer100MovesMoe: parseFloat(columns[csvIndices.moe_price_per_1000_moves]) / 10,
                costPerElo,
                elo,
                eloMoe: parseFloat(columns[csvIndices.elo_moe_95]),
                totalGames: parseInt(columns[csvIndices.total_games], 10)
            };
        })
        .filter(Boolean);
}

function getReasoningLevelRank(level) {
    const normalized = String(level || 'unknown').toLowerCase();
    const qualitativeRanks = {
        none: 0,
        unknown: 1,
        default: 2,
        low: 3,
        medium: 4,
        high: 5,
        xhigh: 6
    };
    if (Object.prototype.hasOwnProperty.call(qualitativeRanks, normalized)) {
        return qualitativeRanks[normalized];
    }

    const budgetMatch = normalized.match(/^budget_(\d+)$/);
    return budgetMatch ? 100 + parseInt(budgetMatch[1], 10) : 1;
}

function getEffortGroups(points) {
    const grouped = new Map();
    points.forEach(point => {
        if (point.reasoningLevel === 'unknown') return;
        if (!grouped.has(point.modeFamily)) {
            grouped.set(point.modeFamily, []);
        }
        grouped.get(point.modeFamily).push(point);
    });

    return Array.from(grouped.values())
        .map(group => group.sort((a, b) =>
            (getReasoningLevelRank(a.reasoningLevel) - getReasoningLevelRank(b.reasoningLevel)) ||
            a.reasoningLevel.localeCompare(b.reasoningLevel) ||
            a.player.localeCompare(b.player)
        ))
        .filter(group => group.length > 1 &&
            new Set(group.map(point => point.reasoningLevel)).size > 1);
}

function getParetoFrontier(points) {
    return points
        .filter(point => !points.some(other =>
            other !== point &&
            other.cost <= point.cost &&
            other.elo >= point.elo &&
            (other.cost < point.cost || other.elo > point.elo)
        ))
        .sort((a, b) => (a.cost - b.cost) || (b.elo - a.elo));
}

function getSparseChartLabels(points, frontier, effortGroups, maxLabels = 24) {
    const frontierSet = new Set(frontier);
    const groupEndpoints = new Set();
    effortGroups.forEach(group => {
        groupEndpoints.add(group[0]);
        groupEndpoints.add(group[group.length - 1]);
    });

    const costs = points.map(point => Math.log10(point.cost));
    const minLogCost = Math.min(...costs);
    const maxLogCost = Math.max(...costs);
    const costRange = Math.max(0.0001, maxLogCost - minLogCost);
    const elos = points.map(point => point.elo);
    const minElo = Math.min(...elos);
    const eloRange = Math.max(1, Math.max(...elos) - minElo);
    const candidates = [...points]
        .filter(point => !frontierSet.has(point))
        .sort((a, b) => {
            const score = point => {
                const costScore = (maxLogCost - Math.log10(point.cost)) / costRange;
                const eloScore = (point.elo - minElo) / eloRange;
                return (groupEndpoints.has(point) ? 300 : 0) +
                    eloScore * 150 +
                    costScore * 100 +
                    (Number.isFinite(point.costPerElo) ? Math.max(0, 50 - point.costPerElo) : 0);
            };
            return score(b) - score(a);
        });

    // Frontier points are always named. Other labels earn a slot only when
    // they are sufficiently separated from labels already selected.
    const selected = [...frontier];
    candidates.forEach(point => {
        if (selected.length >= maxLabels) return;
        const hasNearbyLabel = selected.some(other =>
            Math.abs(other.x - point.x) < 72 &&
            Math.abs(other.y - point.y) < 20
        );
        if (!hasNearbyLabel) selected.push(point);
    });
    return new Set(selected);
}

function getChartLabelText(player) {
    const text = String(player || '');
    return text.length > 27 ? `${text.slice(0, 24)}…` : text;
}

function getChartLabelPlacements(ctx, labelPoints, containerWidth, padding, chartHeight) {
    const plotLeft = padding.left + 4;
    const plotRight = containerWidth - 4;
    const plotTop = padding.top + 4;
    const plotBottom = padding.top + chartHeight - 4;
    const labelHeight = 14;
    const placements = [];

    labelPoints.forEach((point, index) => {
        const text = getChartLabelText(point.player);
        const textWidth = ctx.measureText(text).width;
        const xCandidates = point.x > containerWidth - textWidth - 18 ?
            [point.x - textWidth - 8, point.x + 8] :
            [point.x + 8, point.x - textWidth - 8];
        const yOffsets = index % 2 ? [4, -18, 20, -34] : [-18, 4, -34, 20];

        for (const xCandidate of xCandidates) {
            for (const yOffset of yOffsets) {
                const left = Math.max(plotLeft, Math.min(plotRight - textWidth, xCandidate));
                const top = Math.max(plotTop, Math.min(plotBottom - labelHeight, point.y + yOffset));
                const right = left + textWidth;
                const bottom = top + labelHeight;
                const overlaps = placements.some(existing =>
                    left < existing.right + 4 &&
                    right > existing.left - 4 &&
                    top < existing.bottom + 3 &&
                    bottom > existing.top - 3
                );
                if (!overlaps) {
                    placements.push({ text, left, top, right, bottom, baseline: top + 11 });
                    return;
                }
            }
        }
    });
    return placements;
}

function countChartLabelOverlaps(placements) {
    let overlapCount = 0;
    for (let i = 0; i < placements.length; i++) {
        for (let j = i + 1; j < placements.length; j++) {
            const first = placements[i];
            const second = placements[j];
            if (first.left < second.right &&
                first.right > second.left &&
                first.top < second.bottom &&
                first.bottom > second.top) {
                overlapCount++;
            }
        }
    }
    return overlapCount;
}

function niceTickStep(range, targetCount) {
    const rawStep = range / Math.max(1, targetCount);
    const magnitude = Math.pow(10, Math.floor(Math.log10(rawStep)));
    const normalized = rawStep / magnitude;
    const factor = normalized >= 5 ? 10 : normalized >= 2 ? 5 : normalized >= 1 ? 2 : 1;
    return factor * magnitude;
}

function formatChartMoney(value) {
    if (!Number.isFinite(value)) return 'N/A';
    if (value >= 1) return `$${value.toFixed(2)}`;
    if (value >= 0.01) return `$${value.toFixed(3)}`;
    return `$${value.toFixed(4)}`;
}

function formatChartNumber(value, decimals = 0) {
    return Number.isFinite(value) ? value.toFixed(decimals) : 'N/A';
}

function escapeChartHtml(value) {
    return String(value ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

function renderCostEloPareto() {
    const canvas = document.getElementById('cost-elo-chart');
    const container = document.getElementById('cost-elo-view');
    if (!canvas || !container) return;

    const points = getCostEloPoints();
    const frontier = getParetoFrontier(points);
    const frontierSet = new Set(frontier);
    const effortGroups = getEffortGroups(points);
    const height = costEloExpanded ? Math.max(480, window.innerHeight - 72) : 600;
    const dpr = window.devicePixelRatio || 1;
    const normalWidth = container.clientWidth || 740;
    const containerWidth = costEloExpanded ?
        Math.max(740, window.innerWidth - 48) :
        Math.max(740, normalWidth);
    const padding = { top: 35, right: 30, bottom: 75, left: 90 };
    const chartWidth = Math.max(1, containerWidth - padding.left - padding.right);
    const chartHeight = Math.max(1, height - padding.top - padding.bottom);
    const ctx = canvas.getContext('2d');

    canvas.style.width = `${containerWidth}px`;
    canvas.style.height = `${height}px`;
    canvas.width = containerWidth * dpr;
    canvas.height = height * dpr;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    const tooltipId = 'cost-elo-tooltip';
    const oldTooltip = document.getElementById(tooltipId);
    if (oldTooltip) oldTooltip.remove();

    const tooltip = document.createElement('div');
    tooltip.id = tooltipId;
    Object.assign(tooltip.style, {
        position: 'fixed',
        display: 'none',
        zIndex: '2100',
        maxWidth: '310px',
        padding: '8px',
        backgroundColor: '#333',
        color: 'white',
        boxShadow: '8px 8px black',
        borderRadius: '5px',
        pointerEvents: 'none',
        textAlign: 'left',
        fontSize: '14px',
        fontFamily: '"Web IBM VGA 8x16", monospace'
    });
    document.body.appendChild(tooltip);

    function drawEmptyState() {
        ctx.fillStyle = '#C0C0C0';
        ctx.fillRect(0, 0, containerWidth, height);
        ctx.fillStyle = 'black';
        ctx.font = '16px "Web IBM VGA 8x16", monospace';
        ctx.textAlign = 'center';
        ctx.fillText('No models have valid positive cost and non-negative Elo data.', containerWidth / 2, height / 2);
    }

    if (points.length === 0) {
        drawEmptyState();
        canvas.dataset.labelCount = '0';
        canvas.dataset.labelOverlapCount = '0';
        canvas.dataset.labelClipped = 'false';
        canvas.dataset.effortGroupCount = '0';
        canvas.dataset.highlightedFamily = '';
        canvas.dataset.highlightedVariantCount = '0';
        canvas.onmousemove = null;
        canvas.onmouseleave = null;
        return;
    }

    const costs = points.map(point => point.cost);
    const elos = points.map(point => point.elo);
    let logMin = Math.log10(Math.min(...costs));
    let logMax = Math.log10(Math.max(...costs));
    if (logMin === logMax) {
        logMin -= 0.5;
        logMax += 0.5;
    }

    const eloMin = Math.min(...elos);
    const eloMax = Math.max(...elos);
    const eloRange = Math.max(100, eloMax - eloMin);
    const eloPadding = Math.max(50, eloRange * 0.08);
    const yMin = Math.max(0, eloMin - eloPadding);
    const yMax = eloMax + eloPadding;

    const xForCost = cost => padding.left +
        ((Math.log10(cost) - logMin) / (logMax - logMin)) * chartWidth;
    const yForElo = elo => padding.top +
        ((yMax - elo) / (yMax - yMin)) * chartHeight;

    points.forEach(point => {
        point.x = xForCost(point.cost);
        point.y = yForElo(point.elo);
        point.radius = frontierSet.has(point) ? 7 : 5;
        point.isFrontier = frontierSet.has(point);
    });
    const effortGroupByPoint = new Map();
    effortGroups.forEach(group => {
        group.forEach(point => effortGroupByPoint.set(point, group));
    });
    const labelPoints = getSparseChartLabels(points, frontier, effortGroups);
    canvas.dataset.labelCount = String(labelPoints.size);
    canvas.dataset.effortGroupCount = String(effortGroups.length);

    function getLogTicks() {
        const ticks = [];
        const firstExponent = Math.floor(logMin);
        const lastExponent = Math.ceil(logMax);
        for (let exponent = firstExponent; exponent <= lastExponent; exponent++) {
            [1, 2, 5].forEach(multiplier => {
                const value = multiplier * Math.pow(10, exponent);
                if (value >= Math.pow(10, logMin) && value <= Math.pow(10, logMax)) {
                    ticks.push(value);
                }
            });
        }
        return ticks.length ? ticks : [Math.pow(10, logMin), Math.pow(10, logMax)];
    }

    function getEloTicks() {
        const step = niceTickStep(yMax - yMin, 5);
        const first = Math.ceil(yMin / step) * step;
        const ticks = [];
        for (let value = first; value <= yMax + step * 0.01; value += step) {
            ticks.push(value);
        }
        return ticks.length ? ticks : [yMin, yMax];
    }

    const logTicks = getLogTicks();
    const eloTicks = getEloTicks();

    function drawAxes() {
        ctx.fillStyle = '#C0C0C0';
        ctx.fillRect(0, 0, containerWidth, height);
        ctx.strokeStyle = 'rgba(0, 0, 0, 0.18)';
        ctx.lineWidth = 1;

        logTicks.forEach(value => {
            const x = xForCost(value);
            ctx.beginPath();
            ctx.moveTo(x, padding.top);
            ctx.lineTo(x, padding.top + chartHeight);
            ctx.stroke();
        });
        eloTicks.forEach(value => {
            const y = yForElo(value);
            ctx.beginPath();
            ctx.moveTo(padding.left, y);
            ctx.lineTo(padding.left + chartWidth, y);
            ctx.stroke();
        });

        ctx.strokeStyle = 'black';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(padding.left, padding.top);
        ctx.lineTo(padding.left, padding.top + chartHeight);
        ctx.lineTo(padding.left + chartWidth, padding.top + chartHeight);
        ctx.stroke();

        ctx.fillStyle = 'black';
        ctx.font = '13px "Web IBM VGA 8x16", monospace';
        ctx.textAlign = 'center';
        logTicks.forEach(value => {
            ctx.fillText(formatChartMoney(value), xForCost(value), padding.top + chartHeight + 24);
        });
        ctx.textAlign = 'right';
        eloTicks.forEach(value => {
            ctx.fillText(String(Math.round(value)), padding.left - 10, yForElo(value) + 5);
        });

        ctx.font = '16px "Web IBM VGA 8x16", monospace';
        ctx.textAlign = 'center';
        ctx.fillText('Cost/Game (log scale)', padding.left + chartWidth / 2, height - 20);
        ctx.save();
        ctx.translate(24, padding.top + chartHeight / 2);
        ctx.rotate(-Math.PI / 2);
        ctx.fillText('Elo', 0, 0);
        ctx.restore();
    }

    function drawSeriesLines(hoveredPoint = null) {
        const highlightedGroup = hoveredPoint ? effortGroupByPoint.get(hoveredPoint) : null;
        ctx.lineWidth = 1.5;
        effortGroups.forEach(group => {
            if (group === highlightedGroup) return;
            ctx.strokeStyle = 'rgba(0, 100, 160, 0.45)';
            ctx.beginPath();
            group.forEach((point, index) => {
                if (index === 0) ctx.moveTo(point.x, point.y);
                else ctx.lineTo(point.x, point.y);
            });
            ctx.stroke();
        });

        if (frontier.length > 1) {
            ctx.lineWidth = 3;
            ctx.strokeStyle = '#8b0000';
            ctx.beginPath();
            frontier.forEach((point, index) => {
                if (index === 0) ctx.moveTo(point.x, point.y);
                else ctx.lineTo(point.x, point.y);
            });
            ctx.stroke();
        }

        if (highlightedGroup) {
            ctx.lineWidth = 4;
            ctx.strokeStyle = '#ff8c00';
            ctx.beginPath();
            highlightedGroup.forEach((point, index) => {
                if (index === 0) ctx.moveTo(point.x, point.y);
                else ctx.lineTo(point.x, point.y);
            });
            ctx.stroke();
        }
    }

    function drawPoints(hoveredPoint = null) {
        const highlightedGroup = hoveredPoint ? effortGroupByPoint.get(hoveredPoint) : null;
        points.forEach(point => {
            const isHovered = point === hoveredPoint;
            const isVariantHighlighted = highlightedGroup && highlightedGroup.includes(point);
            ctx.beginPath();
            ctx.arc(point.x, point.y, isHovered ? point.radius + 2 : point.radius, 0, Math.PI * 2);
            ctx.fillStyle = isVariantHighlighted ? '#ff8c00' : (point.isFrontier ? '#ffff00' : '#404040');
            ctx.fill();
            ctx.strokeStyle = isVariantHighlighted || isHovered ? 'white' : 'black';
            ctx.lineWidth = isHovered ? 3 : (isVariantHighlighted ? 2 : 1);
            ctx.stroke();
        });

        ctx.font = '12px "Web IBM VGA 8x16", monospace';
        ctx.fillStyle = 'black';
        const labelPlacements = getChartLabelPlacements(
            ctx,
            labelPoints,
            containerWidth,
            padding,
            chartHeight
        );
        canvas.dataset.labelCount = String(labelPlacements.length);
        canvas.dataset.labelOverlapCount = String(countChartLabelOverlaps(labelPlacements));
        canvas.dataset.labelClipped = String(labelPlacements.some(label =>
            label.left < padding.left ||
            label.right > containerWidth ||
            label.top < padding.top ||
            label.bottom > padding.top + chartHeight
        ));
        ctx.textAlign = 'left';
        labelPlacements.forEach(label => {
            ctx.fillText(label.text, label.left, label.baseline);
        });
    }

    function draw(hoveredPoint = null) {
        drawAxes();
        drawSeriesLines(hoveredPoint);
        drawPoints(hoveredPoint);
    }

    draw();

    function getHoveredPoint(event) {
        const rect = canvas.getBoundingClientRect();
        const scaleX = containerWidth / Math.max(1, rect.width);
        const scaleY = height / Math.max(1, rect.height);
        const mouseX = (event.clientX - rect.left) * scaleX;
        const mouseY = (event.clientY - rect.top) * scaleY;
        let closest = null;
        let closestDistance = Infinity;

        points.forEach(point => {
            const distance = Math.hypot(mouseX - point.x, mouseY - point.y);
            if (distance <= point.radius + 5 && distance < closestDistance) {
                closest = point;
                closestDistance = distance;
            }
        });
        return closest;
    }

    function updateTooltip(point, event) {
        if (!point) {
            tooltip.style.display = 'none';
            return;
        }

        const costMoe = Number.isFinite(point.costMoe) ? ` ± ${formatChartMoney(point.costMoe)}` : '';
        const movesMoe = Number.isFinite(point.costPer100MovesMoe) ?
            ` ± ${formatChartMoney(point.costPer100MovesMoe)}` : '';
        const eloMoe = Number.isFinite(point.eloMoe) ? ` ± ${formatChartNumber(point.eloMoe, 1)}` : '';
        const costPerElo = Number.isFinite(point.costPerElo) ? formatChartMoney(point.costPerElo) : 'N/A';
        tooltip.innerHTML = `<span style="color: yellow; font-weight: bold">${escapeChartHtml(point.player)}</span><br>
Mode family: ${escapeChartHtml(point.modeFamily)}<br>
Reasoning level: ${escapeChartHtml(point.reasoningLevel)}<br>
Elo: ${formatChartNumber(point.elo, 1)}${eloMoe}<br>
Cost/Game: ${formatChartMoney(point.cost)}${costMoe}<br>
Cost/100 Moves: ${formatChartMoney(point.costPer100Moves)}${movesMoe}<br>
Cost/Elo: ${costPerElo}<br>
Games: ${Number.isFinite(point.totalGames) ? point.totalGames : 'N/A'}`;
        tooltip.style.display = 'block';
        const maxLeft = Math.max(8, window.innerWidth - tooltip.offsetWidth - 8);
        const maxTop = Math.max(8, window.innerHeight - tooltip.offsetHeight - 8);
        tooltip.style.left = `${Math.min(event.clientX + 15, maxLeft)}px`;
        tooltip.style.top = `${Math.min(event.clientY + 15, maxTop)}px`;
    }

    canvas.onmousemove = event => {
        const hoveredPoint = getHoveredPoint(event);
        const highlightedGroup = hoveredPoint ? effortGroupByPoint.get(hoveredPoint) : null;
        canvas.dataset.highlightedFamily = highlightedGroup ? highlightedGroup[0].modeFamily : '';
        canvas.dataset.highlightedVariantCount = highlightedGroup ? String(highlightedGroup.length) : '0';
        draw(hoveredPoint);
        updateTooltip(hoveredPoint, event);
    };
    canvas.onmouseleave = () => {
        canvas.dataset.highlightedFamily = '';
        canvas.dataset.highlightedVariantCount = '0';
        draw();
        updateTooltip(null);
    };
}

// Keep the chart responsive without accumulating event listeners.
window.addEventListener('resize', function () {
    if (currentScreen === Screen.COST_ELO) {
        renderCostEloPareto();
    }
});

// Replace buildFreshTable with the updated implementation
function buildFreshTable() {
    const rowObjects = parsedCsvData.rows;

    // Separate regular and special rows
    const normalRows = rowObjects;

    const specialRows = [];

    // Sort normal rows by default criteria first
    normalRows.sort((a, b) => defaultSortFunctions[currentScreen](a.cols, b.cols));

    // Assign ranks that will never change
    normalRows.forEach((row, i) => {
        row.rank = i + 1;
    });

    // Initialize all rows with default primarySort value
    normalRows.forEach(row => {
        row.primarySort = 9999;
    });

    // Combine rows and set as allRows
    allRows = [...normalRows, ...specialRows];

    // Check if there's a saved sort state to restore
    const savedSort = currentSortState[currentScreen];
    if (savedSort && savedSort.columnIndex !== null) {
        // Restore the sort order state for indicators
        sortOrderState[currentScreen][savedSort.columnIndex] = savedSort.order;
        // Apply saved sort (pass order to avoid toggling)
        sortTable(savedSort.columnIndex, savedSort.order);
    } else {
        // Sort with default function
        sortTable();
    }

    // Clear thead and recreate th elements
    const thead = document.querySelector('#leaderboard thead');
    thead.innerHTML = '';

    const headerRow = document.createElement('tr');
    const activeColumns = getActiveColumns();

    activeColumns.forEach((col, i) => {
        const th = document.createElement('th');
        th.textContent = col.title;
        th.setAttribute('title', col.tooltip || col.title);
        th.addEventListener('click', () => sortTable(i));
        headerRow.appendChild(th);
    });
    thead.appendChild(headerRow);

    // Update sort indicator if there's a saved sort
    if (savedSort && savedSort.columnIndex !== null) {
        const sortedHeaderCell = thead.querySelectorAll('th')[savedSort.columnIndex];
        if (sortedHeaderCell) {
            const baseText = sortedHeaderCell.textContent.replace(/[▲▼]/g, '').trim();
            const indicator = savedSort.order === 'asc' ? '▲' : '▼';
            sortedHeaderCell.innerHTML = `${baseText}&nbsp;${indicator}`;
        }
    }
}

// Add function to update table width based on column count
function updateExtendedTableWidth() {
    if (currentScreen !== Screen.LEADERBOARD_EXT) return;

    const container = document.getElementById('leaderboard').querySelector('.table-container');
    if (!container) return;

    // Base number of data columns in standard view (excluding rank and player)
    const baseDataColumns = 3;

    // Get current number of selected data columns
    const currentDataColumns = extendedColumnPreferences.selected.length;

    // Calculate additional margin needed (85px per extra column)
    const extraColumns = Math.max(0, currentDataColumns - baseDataColumns);
    const extraWidth = extraColumns * 85;

    // Base margin is 75px on each side (150px total)
    const baseMargin = 40;

    // Calculate new margins (divide extra width equally)
    const newMargin = baseMargin + Math.floor(extraWidth / 2);

    // Update the container style
    container.style.marginLeft = `-${newMargin}px`;
    container.style.marginRight = `-${newMargin}px`;
}
