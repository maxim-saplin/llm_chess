// Navigation configuration
const navConfig = {
    screens: {
        LEADERBOARD_NEW: {
            id: 'leaderboard_new',
            title: 'Leaderboard',
            elementId: 'leaderboard',
            isDefault: true,
            onShow: function() {
                buildTableGeneric(tableConfigs[this.id]);
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
    moe_games_not_interrupted: 36
};

document.addEventListener('DOMContentLoaded', () => {
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
          compareFn: (a, b) => a.defaultIndex - b.defaultIndex
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

    document.getElementById('total-games').textContent = `Games: ${parseInt(totalGames)}`;
    
    // Add win_loss and game_duration at the top with MoE
    document.getElementById('win_loss').textContent = 
        `Win/Loss: ${parseFloat(winLoss)} ± ${parseFloat(moeWinLoss)}`;
    document.getElementById('game-duration').textContent = 
        `Game Duration: ${parseFloat(gameDuration)} ± ${parseFloat(moeGameDuration)}`;
    
    // Add games interrupted
    document.getElementById('games-interrupted').textContent = 
        `Games Interrupted: ${parseInt(gamesInterrupted)} (${parseFloat(gamesInterruptedPercent/100).toFixed(3)} ± ${parseFloat(moeGamesInterrupted).toFixed(3)})`;
    
    document.getElementById('wins').textContent =
        `Wins: ${parseInt(wins)} (` +
        `${((parseInt(wins) / parseInt(totalGames))).toFixed(3)} ± ${parseFloat(moeWins).toFixed(3)})`;
    document.getElementById('losses').textContent =
        `Losses: ${parseInt(losses)} (` +
        `${((parseInt(losses) / parseInt(totalGames))).toFixed(2)} ± ${parseFloat(moeLosses).toFixed(3)})`;
    document.getElementById('draws').textContent =
        `Draws: ${parseInt(draws)} (` +
        `${((parseInt(draws) / parseInt(totalGames))).toFixed(3)} ± ${parseFloat(moeDraws).toFixed(3)})`;
    document.getElementById('average-moves').textContent = `Average Moves: ${parseFloat(averageMoves).toFixed(2)} ± ${parseFloat(moeAverageMoves).toFixed(2)}`;
    document.getElementById('material-diff').textContent = `Material Diff: ${parseFloat(materialDiff).toFixed(2)} ± ${parseFloat(moeMaterialDiff).toFixed(2)}`;
    document.getElementById('mistakes-per-1000moves').textContent = `Mistakes/1k_Moves: ${parseFloat(mistakesPer1000Moves).toFixed(2)} ± ${parseFloat(moeMistakesPer1000Moves).toFixed(2)}`;
    document.getElementById('completion-tokens-black-per-move').textContent = `Compl.Toks/Move: ${parseFloat(completionTokensBlackPerMove).toFixed(2)} ± ${parseFloat(moeCompletionTokensBlackPerMove).toFixed(2)}`;

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

function buildTableGeneric(config) {
    const lines = data.trim().split('\n').filter(line => line.trim() !== '');
    const rowObjects = lines.slice(1).map((line, i) => {
        const cols = line.split(',');
        return { originalIndex: i, cols };
    });

    // Clear table body
    const tbody = document.querySelector('#leaderboard tbody');
    tbody.innerHTML = '';

    allRows = sortAllRows(rowObjects, config);
    // Assign defaultIndex based on default sort
    allRows.forEach((r, i) => {
        r.defaultIndex = i;
    });

    // Build rows
    allRows.forEach((row, idx) => {
        const tr = document.createElement('tr');
        const isBottomRow = Object.values(SPECIAL_ROWS).includes(row.cols[csvIndices.player]);
        config.columns.forEach((col) => {
            let cellValue;
            if (col.removeFromSpecialRows && isBottomRow) {
                cellValue = '';
            } else if (col.title === '#') {
                // Always show default rank + 1
                cellValue = row.defaultIndex + 1;
            } else {
                cellValue = col.getValue(row.cols, idx);
            }
            const td = document.createElement('td');
            td.textContent = cellValue;
            tr.appendChild(td);
        });
        // Add hover and click
        tr.addEventListener('mouseenter', () => showPlayerDetailsPopup(tr, row.cols));
        tr.addEventListener('mouseleave', hidePopup);
        tr.addEventListener('click', () => showPlayerDetailsPopup(tr, row.cols));

        tbody.appendChild(tr);
    });

    // Clear thead and recreate th elements
    const thead = document.querySelector('#leaderboard thead');
    thead.innerHTML = ''; // Clear existing headers

    const headerRow = document.createElement('tr');
    config.columns.forEach((col, i) => {
        const th = document.createElement('th');
        th.textContent = col.title;
        th.setAttribute('title', col.tooltip || col.title);
        th.addEventListener('click', () => sortTable(i)); // Add click event for sorting
        headerRow.appendChild(th);
    });
    thead.appendChild(headerRow); // Append the new header row to thead
}

function sortTable(columnIndex) {
    const config = tableConfigs[currentScreen];
    const col = config.columns[columnIndex];

    // Determine current sort order
    const sortOrderObj = sortOrderState[currentScreen];
    const currentOrder = sortOrderObj[columnIndex] || 'asc';
    const newOrder = currentOrder === 'asc' ? 'desc' : 'asc';
    sortOrderObj[columnIndex] = newOrder;

    allRows = sortAllRows(allRows, config, columnIndex, newOrder);

    // Re-draw table
    const tbody = document.querySelector('#leaderboard tbody');
    tbody.innerHTML = '';
    allRows.forEach((row, rowIndex) => {
        const tr = document.createElement('tr');
        config.columns.forEach((col, i) => {
            const isBottomRow = Object.values(SPECIAL_ROWS).includes(row.cols[csvIndices.player]);
            let cellValue;
            if (col.removeFromSpecialRows && isBottomRow) {
                cellValue = '';
            } else if (col.title === '#') {
                // Always show default rank + 1
                cellValue = row.defaultIndex + 1;
            } else {
                cellValue = col.getValue(row.cols, rowIndex);
            }
            const td = document.createElement('td');
            td.textContent = cellValue;
            tr.appendChild(td);
        });
        tr.addEventListener('mouseenter', () => showPlayerDetailsPopup(tr, row.cols));
        tr.addEventListener('mouseleave', hidePopup);
        tr.addEventListener('click', () => showPlayerDetailsPopup(tr, row.cols));
        tbody.appendChild(tr);
    });

    // Clear the sort indicators
    document.querySelectorAll('#leaderboard th').forEach(headerCell => {
        const cleanText = headerCell.textContent.replace(/[▲▼]/g, '').trim();
        headerCell.innerHTML = `${cleanText}&nbsp;&nbsp;`;
    });

    // Show indicator for this column
    const sortedHeaderCell = document.querySelectorAll('#leaderboard th')[columnIndex];
    const baseText = sortedHeaderCell.textContent.replace(/[▲▼]/g, '').trim();
    const indicator = sortOrderObj[columnIndex] === 'asc' ? '▲' : '▼';
    sortedHeaderCell.innerHTML = `${baseText}${indicator ? '&nbsp;' + indicator : '&nbsp;&nbsp;'}`;
}
function sortAllRows(rows, config, overrideColumnIndex = null, newOrder = 'asc') {
    // Separate bottom rows
    const bottomRows = [];
    const normalRows = rows.filter(row => {
        const playerName = row.cols[csvIndices.player];
        if (Object.values(SPECIAL_ROWS).includes(playerName)) {
            bottomRows.push(row);
            return false;
        }
        return true;
    });

    // If no override column is given, use default
    if (overrideColumnIndex === null) {
        normalRows.sort((a, b) => config.defaultSortCompare(a.cols, b.cols));
    } else {
        const col = config.columns[overrideColumnIndex];

        normalRows.sort((a, b) => {
            if (col.compareFn) {
                const res = col.compareFn(a, b);
                // For the rank column (#), ignore newOrder and preserve original order
                if (col.title === '#') {
                    return res;
                }
                return newOrder === 'asc' ? res : -res;
            } else {
                const aText = a.cols[overrideColumnIndex].trim();
                const bText = b.cols[overrideColumnIndex].trim();
                const comparison = col.isNumeric
                    ? parseFloat(aText) - parseFloat(bText)
                    : aText.localeCompare(bText);
                return newOrder === 'asc' ? comparison : -comparison;
            }
        });
    }

    // Reassemble and return
    return [...normalRows, ...bottomRows];
}

// Function to render the player matrix visualization
function renderPlayerMatrix() {
    const canvas = document.getElementById('player-matrix');
    const container = document.getElementById('matrix-view');
    
    // Set canvas dimensions to match container
    canvas.width = container.clientWidth;
    canvas.height = 600;
    
    const ctx = canvas.getContext('2d');
    
    // Clear the canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    // Set up dimensions
    const padding = { top: 50, right: 50, bottom: 50, left: 80 };
    const chartWidth = canvas.width - padding.left - padding.right;
    const chartHeight = canvas.height - padding.top - padding.bottom;
    
    // Parse data from the CSV
    const lines = data.trim().split('\n').filter(line => line.trim() !== '');
    
    // Get all models (not just top 10)
    const allRows = lines.slice(1).map(line => {
        const cols = line.split(',');
        return { cols };
    });
    
    // Use the default sort function from tableConfigs to sort rows the same way as the leaderboard
    const config = tableConfigs[Screen.LEADERBOARD_NEW];
    const sortedRows = [...allRows].filter(row => {
        // Filter out special rows
        const playerName = row.cols[csvIndices.player];
        return !Object.values(SPECIAL_ROWS).includes(playerName);
    }).sort((a, b) => config.defaultSortCompare(a.cols, b.cols));
    
    // Get all player names (no top 10 limit)
    const allPlayers = sortedRows.map(row => row.cols[csvIndices.player]);
    
    // Filter data to include all players (not just top 10)
    const playerData = lines.slice(1).filter(line => {
        const cols = line.split(',');
        const playerName = cols[csvIndices.player];
        return allPlayers.includes(playerName);
    }).map(line => {
        const cols = line.split(',');
        return {
            player: cols[csvIndices.player],
            winLossNonInterrupted: parseFloat(cols[csvIndices.win_loss_non_interrupted]) || 0,
            gameDuration: parseFloat(cols[csvIndices.game_duration]) || 0,
            gamesNotInterruptedPercent: parseFloat(cols[csvIndices.games_not_interrupted_percent]) || 0,
            totalGames: parseFloat(cols[csvIndices.total_games]) || 0,
            wins: parseFloat(cols[csvIndices.player_wins]) || 0,
            losses: parseFloat(cols[csvIndices.opponent_wins]) || 0,
            moeWins: parseFloat(cols[csvIndices.moe_black_llm_win_rate]) || 0,
            moeLosses: parseFloat(cols[csvIndices.moe_black_llm_loss_rate]) || 0
        };
    });
    
    // Set fixed min and max values for axes (0% to 100%)
    const minWinLoss = 0;
    const maxWinLoss = 1;
    const minDuration = 0;
    const maxDuration = 1;
    
    // Draw background
    ctx.fillStyle = 'black';
    ctx.fillRect(padding.left, padding.top, chartWidth, chartHeight);
    
    // Draw axes
    ctx.strokeStyle = 'white';
    ctx.lineWidth = 2;
    ctx.beginPath();
    
    // X-axis
    ctx.moveTo(padding.left, padding.top + chartHeight);
    ctx.lineTo(padding.left + chartWidth, padding.top + chartHeight);
    
    // Y-axis
    ctx.moveTo(padding.left, padding.top);
    ctx.lineTo(padding.left, padding.top + chartHeight);
    ctx.stroke();
    
    // Draw grid lines
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.2)';
    ctx.lineWidth = 1;
    
    // X-axis grid lines and labels (0%, 20%, 40%, 60%, 80%, 100%)
    for (let i = 0; i <= 5; i++) {
        const x = padding.left + (chartWidth / 5) * i;
        const value = i * 0.2; // 0 to 1 in steps of 0.2
        
        ctx.beginPath();
        ctx.moveTo(x, padding.top);
        ctx.lineTo(x, padding.top + chartHeight);
        ctx.stroke();
        
        // X-axis label
        ctx.fillStyle = 'white';
        ctx.font = '14px "Web IBM VGA 8x16"';
        ctx.textAlign = 'center';
        ctx.fillText((value * 100).toFixed(0) + '%', x, padding.top + chartHeight + 25);
    }
    
    // Y-axis grid lines and labels (0%, 25%, 50%, 75%, 100%)
    for (let i = 0; i <= 4; i++) {
        const y = padding.top + chartHeight - (chartHeight / 4) * i;
        const value = i * 0.25; // 0 to 1 in steps of 0.25
        
        ctx.beginPath();
        ctx.moveTo(padding.left, y);
        ctx.lineTo(padding.left + chartWidth, y);
        ctx.stroke();
        
        // Y-axis label
        ctx.fillStyle = 'white';
        ctx.font = '14px "Web IBM VGA 8x16"';
        ctx.textAlign = 'right';
        ctx.fillText((value * 100).toFixed(0) + '%', padding.left - 10, y + 5);
    }
    
    // Axis titles
    ctx.fillStyle = 'white';
    ctx.font = '16px "Web IBM VGA 8x16"';
    ctx.textAlign = 'center';
    
    // X-axis title
    ctx.fillText('Game Duration', padding.left + chartWidth / 2, padding.top + chartHeight + 45);
    
    // Y-axis title - rotated
    ctx.save();
    ctx.translate(padding.left - 50, padding.top + chartHeight / 2);
    ctx.rotate(-Math.PI / 2);
    ctx.fillText('Win/Loss (Non-Interrupted)', 0, 0);
    ctx.restore();
    
    // Store point data for hover detection
    const points = [];
    
    // Plot data points
    playerData.forEach((player, _) => {
        // Scale the values to canvas coordinates
        const x = padding.left + chartWidth * (player.gameDuration);
        const y = padding.top + chartHeight - chartHeight * (player.winLossNonInterrupted);
        
        // Draw point
        ctx.beginPath();
        ctx.arc(x, y, 5, 0, Math.PI * 2);
        ctx.fillStyle = 'yellow';
        ctx.fill();
        
        // Store point data for hover with larger hit area for easier hovering
        points.push({
            x: x,
            y: y,
            radius: 10, // Increased from 5 to 10 for easier hover detection
            player: player.player,
            winLossNonInterrupted: player.winLossNonInterrupted,
            gameDuration: player.gameDuration,
            gamesNotInterruptedPercent: player.gamesNotInterruptedPercent,
            totalGames: player.totalGames,
            wins: player.wins,
            losses: player.losses,
            moeWins: player.moeWins,
            moeLosses: player.moeLosses
        });
    });
    
    // Add title
    ctx.fillStyle = 'white';
    ctx.font = '18px "Web IBM VGA 8x16"';
    ctx.textAlign = 'center';
    ctx.fillText('LLM Chess Players Matrix', canvas.width / 2, 25);
    
    // Remove old tooltip if exists
    const oldTooltip = document.getElementById('matrix-tooltip');
    if (oldTooltip) {
        document.body.removeChild(oldTooltip);
    }
    
    // Create new tooltip element
    const tooltipElement = document.createElement('div');
    tooltipElement.id = 'matrix-tooltip';
    tooltipElement.style.position = 'fixed'; // Changed from absolute to fixed for better positioning
    tooltipElement.style.backgroundColor = 'rgba(0, 0, 0, 0.9)';
    tooltipElement.style.color = 'white';
    tooltipElement.style.padding = '8px';
    tooltipElement.style.borderRadius = '5px';
    tooltipElement.style.border = '1px solid #ffffff';
    tooltipElement.style.pointerEvents = 'none';
    tooltipElement.style.display = 'none';
    tooltipElement.style.zIndex = '1000';
    tooltipElement.style.fontSize = '14px';
    tooltipElement.style.fontFamily = '"Web IBM VGA 8x16", monospace';
    document.body.appendChild(tooltipElement);
    
    // Store currently highlighted point for resetting
    let highlightedPoint = null;
    
    // Mouse move handler
    canvas.addEventListener('mousemove', function(e) {
        const rect = canvas.getBoundingClientRect();
        const mouseX = e.clientX - rect.left;
        const mouseY = e.clientY - rect.top;
        
        let hoveredPoint = null;
        
        // Reset previously highlighted point if exists
        if (highlightedPoint) {
            ctx.beginPath();
            ctx.arc(highlightedPoint.x, highlightedPoint.y, 5, 0, Math.PI * 2);
            ctx.fillStyle = 'yellow';
            ctx.fill();
            highlightedPoint = null;
        }
        
        // Check if mouse is over any point
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
        
        // Show tooltip if hovering over a point
        if (hoveredPoint) {
            // Highlight the point
            ctx.beginPath();
            ctx.arc(hoveredPoint.x, hoveredPoint.y, 5, 0, Math.PI * 2);
            ctx.fillStyle = 'lightgreen'; // Change color when hovering
            ctx.fill();
            highlightedPoint = hoveredPoint;
            
            // Show tooltip with model name
            tooltipElement.innerHTML = `${hoveredPoint.player}<br>
Win/Loss (Non-interrupted): ${(hoveredPoint.winLossNonInterrupted * 100).toFixed(1)}%<br>
Game duration: ${(hoveredPoint.gameDuration * 100).toFixed(1)}% moves<br>
Total games: ${hoveredPoint.totalGames}<br>
Wins: ${hoveredPoint.wins} ± ${hoveredPoint.moeWins}<br>
Losses: ${hoveredPoint.losses} ± ${hoveredPoint.moeLosses}<br>
Non-interrupted games: ${hoveredPoint.gamesNotInterruptedPercent}%`;
            tooltipElement.style.left = (e.clientX + 15) + 'px';
            tooltipElement.style.top = (e.clientY - 15) + 'px';
            tooltipElement.style.display = 'block';
            tooltipElement.style.textAlign = 'left';
        } else {
            // Hide tooltip immediately when not over a point
            tooltipElement.style.display = 'none';
        }
    });
    
    // Hide tooltip when mouse leaves canvas
    canvas.addEventListener('mouseleave', function() {
        tooltipElement.style.display = 'none';
        
        // Reset any highlighted point
        if (highlightedPoint) {
            ctx.beginPath();
            ctx.arc(highlightedPoint.x, highlightedPoint.y, 5, 0, Math.PI * 2);
            ctx.fillStyle = 'yellow';
            ctx.fill();
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

// Add this function to your existing code to be called when switching to matrix view
function initializeMatrixView() {
    // Make sure the matrix is rendered at the correct size initially
    setTimeout(renderPlayerMatrix, 0);
}
