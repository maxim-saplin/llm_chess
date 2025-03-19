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
    
    dropdowns: []
};

const Screen = {
    LEADERBOARD_NEW: 'leaderboard_new',
    LEADERBOARD_OLD: 'leaderboard_old',
    HOW_IT_WORKS: 'how_it_works',
    NOTES: 'notes'
};

const SPECIAL_ROWS = {
    STOCKFISH: "Stockfish chess engine (as Black)",
    RANDOM_WHITE: "Random Player (as White)",
    RANDOM_BLACK: "Random Player (as Black)"
};

let sortOrderState = {
    [Screen.LEADERBOARD_NEW]: {},
    [Screen.LEADERBOARD_OLD]: {}
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
    game_duration: 27,
    moe_game_duration: 28,
    games_interrupted: 29,
    games_interrupted_percent: 30,
    moe_games_interrupted: 31
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
          tooltip: 'Model playing as black against Random Player',
          getValue: (cols) => cols[csvIndices.player],
          isNumeric: false,
          compareFn: (a, b) => a.cols[csvIndices.player].localeCompare(b.cols[csvIndices.player])
        },
        {
          title: 'Win/Loss',
          tooltip: 'Win-Loss as a percent',
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
          tooltip: 'Game Duration as a percent',
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
                if (dropbtn) dropbtn.textContent = item.title;
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
    document.getElementById('wins').textContent =
        `Wins: ${parseInt(wins)} (` +
        `${((parseInt(wins) / parseInt(totalGames))).toFixed(3)} ± ${parseFloat(moeWins).toFixed(3)})`;
    document.getElementById('losses').textContent =
        `Losses: ${parseInt(losses)} (` +
        `${((parseInt(losses) / parseInt(totalGames))).toFixed(2)} ± ${parseFloat(moeLosses).toFixed(3)})`;
    const winsMinusLosses = ((parseInt(wins) - parseInt(losses)) / parseInt(totalGames)).toFixed(3);
    document.getElementById('wins_minus_losses').innerHTML = `&nbsp;&nbsp;&nbsp;Wins - Losses: ${winsMinusLosses}`;
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
    
    // Create buttons based on configuration
    Object.values(navConfig.screens).forEach(screen => {
        // Skip screens that should be in dropdowns
        if (isScreenInDropdown(screen.id)) return;
        
        const button = document.createElement('button');
        button.textContent = screen.title;
        button.onclick = () => showPane(screen.id);
        buttonContainer.appendChild(button);
    });
    
    // Create dropdowns
    navConfig.dropdowns.forEach(dropdown => {
        const dropdownContainer = document.createElement('div');
        dropdownContainer.className = 'custom-dropdown';
        
        const dropbtn = document.createElement('button');
        dropbtn.className = 'dropbtn';
        dropbtn.textContent = dropdown.title;
        
        // If dropdown has items, create dropdown content
        if (dropdown.items && dropdown.items.length > 0) {
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
            dropbtn.onclick = () => showPane(dropdown.defaultScreen);
            dropdownContainer.appendChild(dropbtn);
        }
        
        buttonContainer.appendChild(dropdownContainer);
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
        const dropdownConfig = navConfig.dropdowns.find(d => 
            d.title === dropdownContainer.querySelector('.dropbtn').textContent);
        if (dropdownConfig) {
            showPane(dropdownConfig.defaultScreen);
        }
    }
}

// Close the dropdown if clicked outside
window.onclick = function (event) {
    if (!event.target.matches('.dropbtn')) {
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
