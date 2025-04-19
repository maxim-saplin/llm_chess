// Navigation configuration
const navConfig = {
    screens: {
        LEADERBOARD_NEW: {
            id: 'leaderboard_new',
            title: 'Leaderboard',
            elementId: 'leaderboard',
            isDefault: true,
            onShow: function() {
                buildFreshTable(tableConfigs[this.id]);
            }
        },
        MATRIX: {
            id: 'matrix',
            title: 'Matrix',
            elementId: 'matrix-view',
            onShow: function() {
                initializeMatrixView();
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
            onShow: function() {
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
                { title: 'Matrix', screen: 'matrix' }
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

const Screen = {
    LEADERBOARD_NEW: 'leaderboard_new',
    MATRIX: 'matrix',
    HOW_IT_WORKS: 'how_it_works',
    NOTES: 'notes'
};

const SPECIAL_ROWS = {
    STOCKFISH: "Stockfish chess engine (as Black)",
    RANDOM_WHITE: "Random Player (as White)",
    RANDOM_BLACK: "Random Player (as Black)"
};

let sortOrderState = {
    [Screen.LEADERBOARD_NEW]: {}
};

let currentScreen = null;
let allRows = []; // Will store row objects for sorting/drawing

const csvIndices = {
    player: 0,
    total_games: 1,
    player_wins: 2,
    opponent_wins: 3,
    draws: 4,
    player_wins_percent: 5,
    player_draws_percent: 6,
    average_moves: 7,
    moe_average_moves: 8,
    total_moves: 9,
    player_wrong_actions: 10,
    player_wrong_moves: 11,
    wrong_actions_per_1000moves: 12,
    wrong_moves_per_1000moves: 13,
    mistakes_per_1000moves: 14,
    moe_mistakes_per_1000moves: 15,
    player_avg_material: 16,
    opponent_avg_material: 17,
    material_diff_player_llm_minus_opponent: 18,
    moe_material_diff_llm_minus_rand: 19,
    completion_tokens_black_per_move: 20,
    moe_completion_tokens_black_per_move: 21,
    moe_black_llm_win_rate: 22,
    moe_draw_rate: 23,
    moe_black_llm_loss_rate: 24,
    win_loss: 25,
    moe_win_loss: 26,
    win_loss_non_interrupted: 27,
    moe_win_loss_non_interrupted: 28,
    game_duration: 29,
    moe_game_duration: 30,
    games_interrupted: 31,
    games_interrupted_percent: 32,
    moe_games_interrupted: 33,
    games_not_interrupted: 34,
    games_not_interrupted_percent: 35,
    moe_games_not_interrupted: 36,
    average_game_cost: 37,
    moe_average_game_cost: 38
};

// Add this after other global variables
let nextPrimarySortValue = 0; // Track the next available primarySort value

document.addEventListener('DOMContentLoaded', () => {
    // Parse CSV data from the global data variable (loaded from data.js)
    parseCSVData();
    
    // Create navigation elements first
    createNavigation();
    
    // Initialize board animation
    fetchAndAnimateBoard();

    // Show default screen after navigation is created
    showDefaultScreen();
    
    // Initialize markdown rendering
    setTimeout(() => {
        MinimalMD.render('considerations');
    }, 100);
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
    const rowObjects = lines.slice(1).map((line, i) => {
        const cols = line.split(',');
        return { originalIndex: i, cols };
    });
    
    // Separate special rows and normal rows
    parsedCsvData.rows = rowObjects;
    parsedCsvData.specialRows = rowObjects.filter(row => 
        Object.values(SPECIAL_ROWS).includes(row.cols[csvIndices.player]));
    parsedCsvData.normalRows = rowObjects.filter(row => 
        !Object.values(SPECIAL_ROWS).includes(row.cols[csvIndices.player]));
    
    console.log('CSV data parsed successfully');
}

// Define table configs for NEW and OLD leaderboards
const tableConfigs = {
    [Screen.LEADERBOARD_NEW]: {
      columns: [
        {
          title: '#',
          tooltip: 'Rank of the model',
          isNumeric: true,
          removeFromSpecialRows: true,
          getValue: (cols, idx) => '',
          compareFn: (a, b) => a.rank - b.rank
        },
        {
          title: 'Player',
          tooltip: 'Model playing as black against a Random Player',
          getValue: (cols) => cols[csvIndices.player],
          isNumeric: false,
          compareFn: (a, b) => a.cols[csvIndices.player].localeCompare(b.cols[csvIndices.player])
        },
        {
          title: 'Win/Loss',
          tooltip: 'Difference between wins and losses as a percentage of total games (0-100%). This is the primary ranking metric that measures BOTH chess skill AND instruction following ability. A model needs to understand chess strategy AND follow game instructions correctly to score well. 50% represents equal wins/losses, higher scores mean more wins than losses.',
          isNumeric: true,
          getValue: (cols) => {
            const val = parseFloat(cols[csvIndices.win_loss]) || 0;
            return (val * 100).toFixed(2) + '%';
          },
          compareFn: (a, b) => {
            const aVal = parseFloat(a.cols[csvIndices.win_loss]) || 0;
            const bVal = parseFloat(b.cols[csvIndices.win_loss]) || 0;
            return aVal - bVal;
          }
        },
        {
          title: 'Game Duration',
          tooltip: 'Percentage of maximum possible game length completed before termination (0-100%). This specifically measures instruction following reliability across many moves. 100% indicates the model either reached a natural conclusion (checkmate, stalemate) or the maximum 200 moves without protocol violations. Lower scores show the model struggled to maintain correct communication as the game progressed.',
          isNumeric: true,
          getValue: (cols) => {
            const val = parseFloat(cols[csvIndices.game_duration]) || 0;
            return (val * 100).toFixed(2) + '%';
          },
          compareFn: (a, b) => {
            const aVal = parseFloat(a.cols[csvIndices.game_duration]) || 0;
            const bVal = parseFloat(b.cols[csvIndices.game_duration]) || 0;
            return aVal - bVal;
          }
        },
        {
          title: 'Tokens',
          tooltip: 'Number of tokens generated per move. Demonstrates the model\'s verbosity. Lower token counts may indicate efficiency, while higher counts may show more detailed reasoning OR more garbage generation (depending on the overall rank, reasoning models generate more tokens and score better, weak models can also be verbose yet show poor performance).',
          getValue: (cols) => {
            const value = parseFloat(cols[csvIndices.completion_tokens_black_per_move]) || 0;
            return value > 1000 ? value.toFixed(1) : value.toFixed(2);
          },
          isNumeric: true,
          compareFn: (a, b) => {
            const aVal = parseFloat(a.cols[csvIndices.completion_tokens_black_per_move]) || 0;
            const bVal = parseFloat(b.cols[csvIndices.completion_tokens_black_per_move]) || 0;
            return aVal - bVal;
          }
        }
      ],
      defaultSortCompare: (colsA, colsB) => {
        const wlA = parseFloat(colsA[csvIndices.win_loss]) || 0;
        const wlB = parseFloat(colsB[csvIndices.win_loss]) || 0;
        const gdA = parseFloat(colsA[csvIndices.game_duration]) || 0;
        const gdB = parseFloat(colsB[csvIndices.game_duration]) || 0;
        const tokA = parseFloat(colsA[csvIndices.completion_tokens_black_per_move]) || 0;
        const tokB = parseFloat(colsB[csvIndices.completion_tokens_black_per_move]) || 0;
        // Sort by Win/Loss DESC, then Game Duration DESC, then Tokens ASC
        return (wlB - wlA) || (gdB - gdA) || (tokA - tokB);
      }
    },
};

function showPane(screenId) {
    const scrollPos = window.scrollY;
    const screenConfig = Object.values(navConfig.screens).find(s => s.id === screenId);
    
    if (!screenConfig) {
        console.error(`Screen ${screenId} not found in configuration`);
        return;
    }
    
    // Ensure CSV data is parsed if not already done
    if (parsedCsvData.rows.length === 0) {
        parseCSVData();
    }
    
    currentScreen = screenId;
    
    // Hide all panes
    Object.values(navConfig.screens).forEach(screen => {
        const element = document.getElementById(screen.elementId);
        if (element) element.style.display = 'none';
    });
    
    // Show the selected pane
    const selectedElement = document.getElementById(screenConfig.elementId);
    if (selectedElement) selectedElement.style.display = 'block';
    
    // Update button states - add null checks
    document.querySelectorAll('.button-container button').forEach(button => {
        if (button) button.classList.remove('selected');
    });
    
    // Find and select the appropriate button - add null checks
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

    document.getElementById('total-games').innerHTML = 
        `<span>Games:</span> ${parseInt(totalGames)}`;
    document.getElementById('win_loss').innerHTML = 
        `<span>Win/Loss:</span> ${parseFloat(winLoss)} ± ${parseFloat(moeWinLoss)}`;
    document.getElementById('game-duration').innerHTML = 
        `<span>Game Duration:</span> ${parseFloat(gameDuration)} ± ${parseFloat(moeGameDuration)}`;
    document.getElementById('games-interrupted').innerHTML = 
        `<span>Games Interrupted:</span> ${parseInt(gamesInterrupted)} (${parseFloat(gamesInterruptedPercent/100).toFixed(3)} ± ${parseFloat(moeGamesInterrupted).toFixed(3)})`;
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
    popup.style.display = 'none';
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
    const config = tableConfigs[currentScreen];
    const sortOrderObj = sortOrderState[currentScreen];
    
    // If columnIndex is provided, handle sort order toggling
    if (columnIndex !== null) {
        const currentOrder = sortOrderObj[columnIndex] || 'asc';
        newOrder = newOrder || (currentOrder === 'asc' ? 'desc' : 'asc');
        sortOrderObj[columnIndex] = newOrder;
    }
    
    // Separate special rows
    const bottomRows = parsedCsvData.specialRows;
    
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
            return config.defaultSortCompare(a.cols, b.cols);
        } else {
            const col = config.columns[columnIndex];
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
    
    // Combine fixed, unfixed and special rows in the right order
    allRows = [...fixedRows, ...unfixedRows, ...bottomRows];
    
    // Render the table
    renderTable(config);
    
    // Update sort indicators
    if (columnIndex !== null) {
        document.querySelectorAll('#leaderboard th').forEach(headerCell => {
            const cleanText = headerCell.textContent.replace(/[▲▼]/g, '').trim();
            headerCell.innerHTML = `${cleanText}&nbsp;&nbsp;`;
        });
        
        const sortedHeaderCell = document.querySelectorAll('#leaderboard th')[columnIndex];
        const baseText = sortedHeaderCell.textContent.replace(/[▲▼]/g, '').trim();
        const indicator = sortOrderObj[columnIndex] === 'asc' ? '▲' : '▼';
        sortedHeaderCell.innerHTML = `${baseText}${indicator ? '&nbsp;' + indicator : '&nbsp;&nbsp;'}`;
    }
}

function buildFreshTable(config) {
    const rowObjects = parsedCsvData.rows;
    
    // Separate regular and special rows
    const normalRows = rowObjects.filter(row => {
        const playerName = row.cols[csvIndices.player];
        return !Object.values(SPECIAL_ROWS).includes(playerName);
    });
    
    const specialRows = rowObjects.filter(row => {
        const playerName = row.cols[csvIndices.player];
        return Object.values(SPECIAL_ROWS).includes(playerName);
    });
    
    // Sort normal rows by default criteria first
    normalRows.sort((a, b) => config.defaultSortCompare(a.cols, b.cols));
    
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
    
    // Sort with our new function to handle pinned rows
    sortTable();
    
    // Clear thead and recreate th elements
    const thead = document.querySelector('#leaderboard thead');
    thead.innerHTML = '';

    const headerRow = document.createElement('tr');
    config.columns.forEach((col, i) => {
        const th = document.createElement('th');
        th.textContent = col.title;
        th.setAttribute('title', col.tooltip || col.title);
        th.addEventListener('click', () => sortTable(i));
        headerRow.appendChild(th);
    });
    thead.appendChild(headerRow);
}

function initializeMatrixView() {
    // Then render the matrix
    setTimeout(renderPlayerMatrix, 0);
}

// Function to render the player matrix visualization
function renderPlayerMatrix() {
    // Configuration
    const config = {
        padding: { top: 20, right: 50, bottom: 60, left: 80 },
        height: 600,
        pointRadius: 5,
        hoverRadius: 10,
        colors: {
            background: '#C0C0C0',
            axes: 'black',
            gridLines: 'rgba(0, 0, 0, 0.2)',
            points: '#404040',
            pointHover: 'yellow',
            labels: 'black'
        },
        fonts: {
            axis: '14px "Web IBM VGA 8x16"',
            title: '16px "Web IBM VGA 8x16"',
            labels: '12px "Web IBM VGA 8x16"'
        },
        titles: {
            x: 'Game Duration',
            // y: 'Win/Loss (Non-Interrupted)'
            y: 'Win Rate'
        },
        tooltip: {
            style: {
                position: 'fixed',
                backgroundColor: '#333',
                color: 'white',
                padding: '8px',
                boxShadow: '8px 8px black',
                borderRadius: '5px',
                border: 'none',
                pointerEvents: 'none',
                display: 'none',
                zIndex: '1000',
                fontSize: '14px',
                fontFamily: '"Web IBM VGA 8x16", monospace'
            }
        },
        // Simple hardcoded list of models to label
        labeledModels: ["claude-v3-7-sonnet-thinking_1024", "o4-mini-2025-04-16-low", "o1-2024-12-17-low", "o1-preview-2024-09-12", "o3-mini-2025-01-31-medium", "o1-mini-2024-09-12", "deepseek-reasoner-r1", "claude-v3-5-sonnet-v1", "grok-2-1212", "gemini-2.0-flash-lite-001" ]
    };

    const canvas = document.getElementById('player-matrix');
    const container = document.getElementById('matrix-view');
    
    // Get the device pixel ratio
    const dpr = window.devicePixelRatio || 1;
    
    // Set canvas dimensions accounting for device pixel ratio
    const containerWidth = container.clientWidth;
    canvas.style.width = containerWidth + 'px';
    canvas.style.height = config.height + 'px';
    canvas.width = containerWidth * dpr;
    canvas.height = config.height * dpr;
    
    const ctx = canvas.getContext('2d');
    
    // Scale all drawing operations by the device pixel ratio
    ctx.scale(dpr, dpr);
    
    const chartWidth = containerWidth - config.padding.left - config.padding.right;
    const chartHeight = config.height - config.padding.top - config.padding.bottom;
    
    ctx.fillStyle = config.colors.background;
    ctx.fillRect(0, 0, containerWidth, config.height);
    
    // Use pre-parsed data instead of parsing again
    const normalRows = parsedCsvData.normalRows;
    
    // Use the default sort function from tableConfigs to sort rows the same way as the leaderboard
    const tableConfig = tableConfigs[Screen.LEADERBOARD_NEW];
    const sortedRows = [...normalRows].sort((a, b) => 
        tableConfig.defaultSortCompare(a.cols, b.cols));
    
    // Get all player names (no top 10 limit)
    const allPlayers = sortedRows.map(row => row.cols[csvIndices.player]);
    
    // Map to the format needed for the visualization
    const playerData = sortedRows.map(row => {
        const cols = row.cols;
        return {
            player: cols[csvIndices.player],
            // winLossNonInterrupted: parseFloat(cols[csvIndices.win_loss_non_interrupted]) || 0,
            winRate: parseFloat(cols[csvIndices.player_wins]) / parseFloat(cols[csvIndices.total_games]) || 0,
            gameDuration: parseFloat(cols[csvIndices.game_duration]) || 0,
            averageMoves: parseFloat(cols[csvIndices.average_moves]) || 0,
            moeAverageMoves: parseFloat(cols[csvIndices.moe_average_moves]) || 0,
            gamesNotInterruptedPercent: parseFloat(cols[csvIndices.games_not_interrupted_percent]) || 0,
            totalGames: parseFloat(cols[csvIndices.total_games]) || 0,
            wins: parseFloat(cols[csvIndices.player_wins]) || 0,
            losses: parseFloat(cols[csvIndices.opponent_wins]) || 0,
            moeWins: parseFloat(cols[csvIndices.moe_black_llm_win_rate]) || 0,
            moeLosses: parseFloat(cols[csvIndices.moe_black_llm_loss_rate]) || 0
        };
    });
    
    // Draw axes
    ctx.strokeStyle = config.colors.axes;
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(config.padding.left, config.padding.top + chartHeight);
    ctx.lineTo(config.padding.left + chartWidth, config.padding.top + chartHeight);
    ctx.moveTo(config.padding.left, config.padding.top);
    ctx.lineTo(config.padding.left, config.padding.top + chartHeight);
    ctx.stroke();
    
    // Draw grid lines
    ctx.strokeStyle = config.colors.gridLines;
    ctx.lineWidth = 1;
    
    // X-axis grid lines and labels (0%, 20%, 40%, 60%, 80%, 100%)
    for (let i = 0; i <= 5; i++) {
        const x = config.padding.left + (chartWidth / 5) * i;
        const value = i * 0.2;
        
        ctx.beginPath();
        ctx.moveTo(x, config.padding.top);
        ctx.lineTo(x, config.padding.top + chartHeight);
        ctx.stroke();
        
        ctx.fillStyle = config.colors.axes;
        ctx.font = config.fonts.axis;
        ctx.textAlign = 'center';
        ctx.fillText((value * 100).toFixed(0) + '%', x, config.padding.top + chartHeight + 25);
    }
    
    // Y-axis grid lines and labels (0%, 25%, 50%, 75%, 100%)
    for (let i = 0; i <= 4; i++) {
        const y = config.padding.top + chartHeight - (chartHeight / 4) * i;
        const value = i * 0.25;
        
        ctx.beginPath();
        ctx.moveTo(config.padding.left, y);
        ctx.lineTo(config.padding.left + chartWidth, y);
        ctx.stroke();
        
        ctx.fillStyle = config.colors.axes;
        ctx.font = config.fonts.axis;
        ctx.textAlign = 'right';
        ctx.fillText((value * 100).toFixed(0) + '%', config.padding.left - 10, y + 5);
    }
    
    // Axis titles
    ctx.fillStyle = config.colors.axes;
    ctx.font = config.fonts.title;
    ctx.textAlign = 'center';
    
    // X-axis title
    ctx.fillText(config.titles.x, config.padding.left + chartWidth / 2, config.padding.top + chartHeight + 45);
    
    // Y-axis title - rotated
    ctx.save();
    ctx.translate(config.padding.left - 50, config.padding.top + chartHeight / 2);
    ctx.rotate(-Math.PI / 2);
    ctx.fillText(config.titles.y, 0, 0);
    ctx.restore();
    
    // Store point data for hover detection
    const points = [];
    
    // Plot data points
    playerData.forEach((player, _) => {
        const x = config.padding.left + chartWidth * (player.gameDuration);
        // const y = config.padding.top + chartHeight - chartHeight * (player.winLossNonInterrupted);
        const y = config.padding.top + chartHeight - chartHeight * (player.winRate);
        
        ctx.beginPath();
        ctx.arc(x, y, config.pointRadius, 0, Math.PI * 2);
        ctx.fillStyle = config.colors.points;
        ctx.fill();
        
        // Draw labels for selected models
        if (config.labeledModels.includes(player.player)) {
            ctx.fillStyle = config.colors.labels;
            ctx.font = config.fonts.labels;
            
            // Measure text width to determine if it will be clipped
            const textWidth = ctx.measureText(player.player).width;
            const rightEdgeX = config.padding.left + chartWidth;
            const bottomEdgeY = config.padding.top + chartHeight;
            
            // Determine text alignment and position
            if (x + textWidth + 10 > rightEdgeX) {
                // Too close to right edge, place text to the left
                ctx.textAlign = 'right';
                ctx.fillText(player.player, x - config.pointRadius - 5, y);
            } else {
                // Default: place text to the right
                ctx.textAlign = 'left';
                ctx.fillText(player.player, x + config.pointRadius + 5, y);
            }
        }
        
        const point = {
            x: x,
            y: y,
            radius: config.hoverRadius
        };
        
        for (const [key, value] of Object.entries(player)) {
            point[key] = value;
        }
        
        points.push(point);
    });
    
    // Remove old tooltip if exists
    const oldTooltip = document.getElementById('matrix-tooltip');
    if (oldTooltip) {
        document.body.removeChild(oldTooltip);
    }
    
    // Create new tooltip element
    const tooltipElement = document.createElement('div');
    tooltipElement.id = 'matrix-tooltip';
    Object.assign(tooltipElement.style, config.tooltip.style);
    document.body.appendChild(tooltipElement);
    
    let highlightedPoint = null;
    
    // Mouse move handler
    canvas.addEventListener('mousemove', function(e) {
        const rect = canvas.getBoundingClientRect();
        const mouseX = e.clientX - rect.left;
        const mouseY = e.clientY - rect.top;
        
        let hoveredPoint = null;
        
        // Find if we're hovering over a point
        for (const point of points) {
            const distance = Math.sqrt(
                Math.pow(mouseX - point.x, 2) + 
                Math.pow(mouseY - point.y, 2)
            );
            
            if (distance <= point.radius) {
                hoveredPoint = point;
                break;
            }
        }
        
        // Only redraw if hover state changes
        if ((hoveredPoint && !highlightedPoint) || 
            (!hoveredPoint && highlightedPoint) || 
            (hoveredPoint && highlightedPoint && hoveredPoint.player !== highlightedPoint.player)) {
            
            // Redraw the entire chart
            ctx.clearRect(0, 0, containerWidth, config.height);
            
            // Redraw background
            ctx.fillStyle = config.colors.background;
            ctx.fillRect(0, 0, containerWidth, config.height);
            
            // Redraw axes
            ctx.strokeStyle = config.colors.axes;
            ctx.lineWidth = 2;
            ctx.beginPath();
            ctx.moveTo(config.padding.left, config.padding.top + chartHeight);
            ctx.lineTo(config.padding.left + chartWidth, config.padding.top + chartHeight);
            ctx.moveTo(config.padding.left, config.padding.top);
            ctx.lineTo(config.padding.left, config.padding.top + chartHeight);
            ctx.stroke();
            
            // Redraw grid lines and labels
            ctx.strokeStyle = config.colors.gridLines;
            ctx.lineWidth = 1;
            
            // X-axis grid lines and labels
            for (let i = 0; i <= 5; i++) {
                const x = config.padding.left + (chartWidth / 5) * i;
                const value = i * 0.2;
                
                ctx.beginPath();
                ctx.moveTo(x, config.padding.top);
                ctx.lineTo(x, config.padding.top + chartHeight);
                ctx.stroke();
                
                ctx.fillStyle = config.colors.axes;
                ctx.font = config.fonts.axis;
                ctx.textAlign = 'center';
                ctx.fillText((value * 100).toFixed(0) + '%', x, config.padding.top + chartHeight + 25);
            }
            
            // Y-axis grid lines and labels
            for (let i = 0; i <= 4; i++) {
                const y = config.padding.top + chartHeight - (chartHeight / 4) * i;
                const value = i * 0.25;
                
                ctx.beginPath();
                ctx.moveTo(config.padding.left, y);
                ctx.lineTo(config.padding.left + chartWidth, y);
                ctx.stroke();
                
                ctx.fillStyle = config.colors.axes;
                ctx.font = config.fonts.axis;
                ctx.textAlign = 'right';
                ctx.fillText((value * 100).toFixed(0) + '%', config.padding.left - 10, y + 5);
            }
            
            // Redraw axis titles
            ctx.fillStyle = config.colors.axes;
            ctx.font = config.fonts.title;
            ctx.textAlign = 'center';
            
            // X-axis title
            ctx.fillText(config.titles.x, config.padding.left + chartWidth / 2, config.padding.top + chartHeight + 45);
            
            // Y-axis title - rotated
            ctx.save();
            ctx.translate(config.padding.left - 50, config.padding.top + chartHeight / 2);
            ctx.rotate(-Math.PI / 2);
            ctx.fillText(config.titles.y, 0, 0);
            ctx.restore();
            
            // Draw all points and labels
            points.forEach(point => {
                const isHighlighted = hoveredPoint && point.player === hoveredPoint.player;
                
                ctx.beginPath();
                ctx.arc(point.x, point.y, config.pointRadius, 0, Math.PI * 2);
                ctx.fillStyle = isHighlighted ? config.colors.pointHover : config.colors.points;
                ctx.fill();
                
                // Draw labels for selected models
                if (config.labeledModels.includes(point.player)) {
                    ctx.fillStyle = config.colors.labels;
                    ctx.font = config.fonts.labels;
                    
                    // Measure text width to determine if it will be clipped
                    const textWidth = ctx.measureText(point.player).width;
                    const rightEdgeX = config.padding.left + chartWidth;
                    
                    // Determine text alignment and position
                    if (point.x + textWidth + 10 > rightEdgeX) {
                        // Too close to right edge, place text to the left
                        ctx.textAlign = 'right';
                        ctx.fillText(point.player, point.x - config.pointRadius - 5, point.y);
                    } else {
                        // Default: place text to the right
                        ctx.textAlign = 'left';
                        ctx.fillText(point.player, point.x + config.pointRadius + 5, point.y);
                    }
                }
            });
            
            // Update highlighted point reference
            highlightedPoint = hoveredPoint;
        }
        
        // Update tooltip
        if (hoveredPoint) {
            tooltipElement.innerHTML = `<span style="color: yellow; font-weight: bold">${hoveredPoint.player}</span><br>
Win Rate: ${(hoveredPoint.winRate * 100).toFixed(1)}%<br>
Game duration: ${(hoveredPoint.gameDuration * 100).toFixed(1)}%<br>
Average moves: ${hoveredPoint.averageMoves} ± ${hoveredPoint.moeAverageMoves}<br>
Total games: ${hoveredPoint.totalGames}<br>
Wins: ${hoveredPoint.wins} ± ${hoveredPoint.moeWins}<br>
Losses: ${hoveredPoint.losses} ± ${hoveredPoint.moeLosses}<br>
Non-interrupted games: ${hoveredPoint.gamesNotInterruptedPercent}%`;
            tooltipElement.style.left = (e.clientX + 15) + 'px';
            tooltipElement.style.top = (e.clientY - 15) + 'px';
            tooltipElement.style.display = 'block';
            tooltipElement.style.textAlign = 'left';
        } else {
            tooltipElement.style.display = 'none';
        }
    });
    
    canvas.addEventListener('mouseleave', function() {
        tooltipElement.style.display = 'none';
        
        if (highlightedPoint) {
            // Redraw the entire chart to its initial state
            ctx.clearRect(0, 0, containerWidth, config.height);
            
            // Redraw background
            ctx.fillStyle = config.colors.background;
            ctx.fillRect(0, 0, containerWidth, config.height);
            
            // Redraw axes
            ctx.strokeStyle = config.colors.axes;
            ctx.lineWidth = 2;
            ctx.beginPath();
            ctx.moveTo(config.padding.left, config.padding.top + chartHeight);
            ctx.lineTo(config.padding.left + chartWidth, config.padding.top + chartHeight);
            ctx.moveTo(config.padding.left, config.padding.top);
            ctx.lineTo(config.padding.left, config.padding.top + chartHeight);
            ctx.stroke();
            
            // Redraw grid lines and labels
            ctx.strokeStyle = config.colors.gridLines;
            ctx.lineWidth = 1;
            
            // X-axis grid lines and labels
            for (let i = 0; i <= 5; i++) {
                const x = config.padding.left + (chartWidth / 5) * i;
                const value = i * 0.2;
                
                ctx.beginPath();
                ctx.moveTo(x, config.padding.top);
                ctx.lineTo(x, config.padding.top + chartHeight);
                ctx.stroke();
                
                ctx.fillStyle = config.colors.axes;
                ctx.font = config.fonts.axis;
                ctx.textAlign = 'center';
                ctx.fillText((value * 100).toFixed(0) + '%', x, config.padding.top + chartHeight + 25);
            }
            
            // Y-axis grid lines and labels
            for (let i = 0; i <= 4; i++) {
                const y = config.padding.top + chartHeight - (chartHeight / 4) * i;
                const value = i * 0.25;
                
                ctx.beginPath();
                ctx.moveTo(config.padding.left, y);
                ctx.lineTo(config.padding.left + chartWidth, y);
                ctx.stroke();
                
                ctx.fillStyle = config.colors.axes;
                ctx.font = config.fonts.axis;
                ctx.textAlign = 'right';
                ctx.fillText((value * 100).toFixed(0) + '%', config.padding.left - 10, y + 5);
            }
            
            // Redraw axis titles
            ctx.fillStyle = config.colors.axes;
            ctx.font = config.fonts.title;
            ctx.textAlign = 'center';
            
            // X-axis title
            ctx.fillText(config.titles.x, config.padding.left + chartWidth / 2, config.padding.top + chartHeight + 45);
            
            // Y-axis title - rotated
            ctx.save();
            ctx.translate(config.padding.left - 50, config.padding.top + chartHeight / 2);
            ctx.rotate(-Math.PI / 2);
            ctx.fillText(config.titles.y, 0, 0);
            ctx.restore();
            
            // Draw all points and labels in normal state
            points.forEach(point => {
                ctx.beginPath();
                ctx.arc(point.x, point.y, config.pointRadius, 0, Math.PI * 2);
                ctx.fillStyle = config.colors.points;
                ctx.fill();
                
                // Draw labels for selected models
                if (config.labeledModels.includes(point.player)) {
                    ctx.fillStyle = config.colors.labels;
                    ctx.font = config.fonts.labels;
                    
                    // Measure text width to determine if it will be clipped
                    const textWidth = ctx.measureText(point.player).width;
                    const rightEdgeX = config.padding.left + chartWidth;
                    
                    // Determine text alignment and position
                    if (point.x + textWidth + 10 > rightEdgeX) {
                        // Too close to right edge, place text to the left
                        ctx.textAlign = 'right';
                        ctx.fillText(point.player, point.x - config.pointRadius - 5, point.y);
                    } else {
                        // Default: place text to the right
                        ctx.textAlign = 'left';
                        ctx.fillText(point.player, point.x + config.pointRadius + 5, point.y);
                    }
                }
            });
            
            highlightedPoint = null;
        }
    });
}

// Add window resize handler to make the matrix responsive
window.addEventListener('resize', function() {
    if (currentScreen === Screen.MATRIX) {
        renderPlayerMatrix();
    }
});

function renderTable(config) {
    const tbody = document.querySelector('#leaderboard tbody');
    tbody.innerHTML = '';

    allRows.forEach((row, idx) => {
        const tr = document.createElement('tr');
        const isBottomRow = Object.values(SPECIAL_ROWS).includes(row.cols[csvIndices.player]);
        
        // Add 'fixed' class to rows with primarySort < 9999
        if (row.primarySort !== undefined && row.primarySort < 9999) {
            tr.classList.add('fixed');
        }
        
        config.columns.forEach((col) => {
            let cellValue;
            if (col.removeFromSpecialRows && isBottomRow) {
                cellValue = '';
            } else if (col.title === '#') {
                // Always use the original rank (assigned once during buildFreshTable)
                cellValue = row.rank || '';
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
            toggleRowFixed(row, config);
        });
        tr.addEventListener('click', () => {
            showPlayerDetailsPopup(tr, row.cols);
        });
        
        tbody.appendChild(tr);
    });
}

function toggleRowFixed(row, config) {
    const isBottomRow = Object.values(SPECIAL_ROWS).includes(row.cols[csvIndices.player]);
    
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