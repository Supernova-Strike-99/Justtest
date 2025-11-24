// game_logic.c - core Tetris game state, physics and scoring

#include "tetris.h"

// globals(game state)

int CELL = 26;

int GRID_X = 40;
int GRID_Y = 80;

char Table[ROWS][COLS];   // Board grid: 0 = empty, 1 = filled
int score = 0;
int GameOn = TRUE;
int timer_ms = BASE_TIMER_MS;
int level = 0;

Node *head = NULL;        // Shape queue head
Node *tail = NULL;        // Shape queue tail

Shape current = { NULL, 0, 0, 0 }; // Currently falling piece

// shapes

// Constant shape definitions (like a small texture atlas)
const signed char S0_0[3][3] = {{0,1,1},{1,1,0},{0,0,0}};
const signed char S1_0[3][3] = {{1,1,0},{0,1,1},{0,0,0}};
const signed char S2_0[3][3] = {{0,1,0},{1,1,1},{0,0,0}};
const signed char S3_0[3][3] = {{0,0,1},{1,1,1},{0,0,0}};
const signed char S4_0[3][3] = {{1,0,0},{1,1,1},{0,0,0}};
const signed char S5_0[2][2] = {{1,1},{1,1}};
const signed char S6_0[4][4] = {{0,0,0,0},{1,1,1,1},{0,0,0,0},{0,0,0,0}};

// Logical widths of each shape
const int ShapeWidths[7] = {3,3,3,3,3,2,4};

// linked list/queue

// Append a shape index into the "next pieces" queue
void enqueueShape(int shapeIndex) {
    Node *newNode = (Node *)malloc(sizeof(Node));
    newNode->shapeIndex = shapeIndex;
    newNode->next = NULL;

    if (!tail) {
        head = tail = newNode;
    } else {
        tail->next = newNode;
        tail = newNode;
    }
}

// Pop oldest shape index from queue (random if empty)
int dequeueShape() {
    if (!head) return rand() % 7;
    Node *temp = head;
    int val = temp->shapeIndex;
    head = head->next;
    if (!head) tail = NULL;
    free(temp);
    return val;
}

// Peek next shape index without removing it (random if nothing queued)
int peekNextShape() {
    if (head) return head->shapeIndex;
    return rand() % 7;
}

// Free the whole queue
void freeQueue() {
    while (head) {
        Node *tmp = head;
        head = head->next;
        free(tmp);
    }
    tail = NULL;
}

// shape memory helpers

// Free heap memory of a Shape safely
void safe_free_shape(Shape *s) {
    if (!s || !s->array) return;
    for (int i = 0; i < s->width; ++i) free(s->array[i]);
    free(s->array);
    s->array = NULL;
    s->width = 0;
}

// Allocate a square matrix width*width for a Shape
static void alloc_shape_square(Shape *s, int w) {
    s->width = w;
    s->array = (char **)malloc(w * sizeof(char*));
    for (int i = 0; i < w; ++i) {
        s->array[i] = (char*)calloc(w, sizeof(char));
    }
}

// Copy shape data from the constant templates into a heap Shape
Shape make_copy_from_constshape(int index) {
    Shape s = (Shape){NULL, 0, 0, 0};
    if (index < 0 || index > 6) return s;

    int w = ShapeWidths[index];
    alloc_shape_square(&s, w);

    const signed char *src = NULL;
    switch (index) {
        case 0: src = &S0_0[0][0]; break;
        case 1: src = &S1_0[0][0]; break;
        case 2: src = &S2_0[0][0]; break;
        case 3: src = &S3_0[0][0]; break;
        case 4: src = &S4_0[0][0]; break;
        case 5: src = &S5_0[0][0]; break;
        case 6: src = &S6_0[0][0]; break;
    }

    // Copy into dynamic array
    for (int i = 0; i < w; ++i)
        for (int j = 0; j < w; ++j)
            s.array[i][j] = (char)src[i * w + j];

    return s;
}

// position checks and rotation

// Check if a shape is in a valid position given (row, col)
int CheckPositionAt(char **array, int width, int row, int col) {
    for (int i = 0; i < width; ++i)
        for (int j = 0; j < width; ++j)
            if (array[i][j]) {
                int tr = row + i, tc = col + j;
                if (tc < 0 || tc >= COLS || tr >= ROWS) return FALSE;
                if (tr >= 0 && Table[tr][tc]) return FALSE;
            }
    return TRUE;
}

// Same as above but operates on a temporary stack buffer
int CheckPositionBuf(char buf[4][4], int width, int row, int col) {
    for (int i = 0; i < width; ++i)
        for (int j = 0; j < width; ++j)
            if (buf[i][j]) {
                int tr = row + i, tc = col + j;
                if (tc < 0 || tc >= COLS || tr >= ROWS) return FALSE;
                if (tr >= 0 && Table[tr][tc]) return FALSE;
            }
    return TRUE;
}

// Generate a rotated version of a shape into buf (clockwise rotation)
void make_rotated_buffer(char buf[4][4], char **src, int width) {
    for (int i = 0; i < width; ++i)
        for (int j = 0; j < width; ++j)
            buf[i][j] = src[width - 1 - j][i];
}

// Copy rotated buffer back onto the current shape
void apply_rotated_to_current(char buf[4][4], int width) {
    for (int i = 0; i < width; ++i)
        for (int j = 0; j < width; ++j)
            current.array[i][j] = buf[i][j];
}

// core game logic

// Spawn a new current shape, centered at the top
void SetNewRandomShape(int shapeIndex) {
    Shape new_shape = make_copy_from_constshape(shapeIndex);
    new_shape.col = rand() % (COLS - new_shape.width + 1);
    new_shape.row = 0;

    safe_free_shape(&current);
    current = new_shape;

    // If we can't place new shape, it's game over
    if (!CheckPositionAt(current.array, current.width, current.row, current.col))
        GameOn = FALSE;
}

// Lock the current shape into the table grid
void WriteToTable(void) {
    for (int i = 0; i < current.width; ++i)
        for (int j = 0; j < current.width; ++j)
            if (current.array[i][j]) {
                int tr = current.row + i, tc = current.col + j;
                if (tr >= 0 && tr < ROWS && tc >= 0 && tc < COLS)
                    Table[tr][tc] = 1;
            }
}

// Attempt to rotate current shape, with simple "wall kick" offsets
void RotateCurrentIfPossible(void) {
    if (!current.array) return;

    int w = current.width;
    char buf[4][4] = {{0}};

    make_rotated_buffer(buf, current.array, w);

    // Small set of translation attempts after rotation
    int kicks[5][2] = {{0,0},{0,-1},{0,1},{-1,0},{0,-2}};
    for (int k = 0; k < 5; ++k) {
        int r = current.row + kicks[k][0];
        int c = current.col + kicks[k][1];
        if (CheckPositionBuf(buf, w, r, c)) {
            apply_rotated_to_current(buf, w);
            current.row = r;
            current.col = c;
            return;
        }
    }
}

// Move / rotate current shape based on action; shapeIndex used when locking
int ManipulateCurrent(int action, int *shapeIndex) {
    if (!current.array) return 0;
    int changed = 0;

    if (action == 's') {
        // Move down or lock if we can't
        if (CheckPositionAt(current.array, current.width, current.row + 1, current.col)) {
            current.row++;
            changed = 1;
        } else {
            WriteToTable();
            RemoveFullRowsAndUpdateScore();
            *shapeIndex = dequeueShape();
            enqueueShape(rand() % 7);
            SetNewRandomShape(*shapeIndex);
            changed = 1;
        }
    } else if (action == 'a') {
        if (CheckPositionAt(current.array, current.width, current.row, current.col - 1)) {
            current.col--;
            changed = 1;
        }
    } else if (action == 'd') {
        if (CheckPositionAt(current.array, current.width, current.row, current.col + 1)) {
            current.col++;
            changed = 1;
        }
    } else if (action == 'w') {
        RotateCurrentIfPossible();
        changed = 1;
    }

    return changed;
}

// Scan for full lines, flash them, remove them, update score & speed
void RemoveFullRowsAndUpdateScore(void) {
    int lines = 0;

    for (int i = ROWS - 1; i >= 0; --i) {
        int full = 1;
        for (int j = 0; j < COLS; ++j)
            if (!Table[i][j]) {
                full = 0;
                break;
            }

        if (full) {
            // Flash the row white before removing it (simple feedback)
            for (int f = 0; f < 4; f++) {
                BeginDrawing();
                ClearBackground((Color){20, 20, 20, 255});
                DrawRectangleGradientV(0, 0, GetScreenWidth(), GetScreenHeight(),
                                       (Color){10, 10, 10, 255}, (Color){35, 35, 35, 255});

                // Draw grid with current state
                drawGridAndCurrent();

                // Draw sidebar (HUD) so it doesn’t blink away
                drawSidebar(currentPlayer, 0);

                // Flash white row
                for (int x = 0; x < COLS; x++) {
                    Rectangle rect = {
                        (float)(GRID_X + x * CELL),
                        (float)(GRID_Y + i * CELL),
                        (float)(CELL - 2),
                        (float)(CELL - 2)
                    };
                    DrawRectangleRec(rect, WHITE);
                }

                EndDrawing();
                WaitTime(0.05);
            }

            // Remove full line by pulling everything above down
            lines++;
            for (int k = i; k > 0; --k)
                memcpy(Table[k], Table[k - 1], COLS);
            memset(Table[0], 0, COLS);

            i = ROWS; // restart scan from bottom after collapse
        }
    }

    // Update score and gravity timer
    if (lines) {
        score += 100 * lines;
        timer_ms = (timer_ms > MIN_TIMER_MS + 20)
            ? timer_ms - 20
            : MIN_TIMER_MS;
    }
}

/// reset/game wrapper

// Reset board, score, queue and spawn first shape
void resetGameState(void) {
    memset(Table, 0, sizeof(Table));
    score    = 0;
    level    = 0;
    timer_ms = BASE_TIMER_MS;
    GameOn   = TRUE;

    safe_free_shape(&current);
    freeQueue();

    // Pre-fill queue with a few random shapes
    for (int i = 0; i < 3; ++i) {
        enqueueShape(rand() % 7);
    }

    int shapeIndex = dequeueShape();
    enqueueShape(rand() % 7);
    SetNewRandomShape(shapeIndex);
}

// save screens / GAME OVER

// Ask whether to save this session's score; returns 1 if player chose to save
int askSaveDataScreen(int finalScore) {
    SetExitKey(KEY_NULL);
    while (!WindowShouldClose()) {
        BeginDrawing();
        ClearBackground(BLACK);

        const char *msg = "Save this game data?";
        const char *scoreMsg = TextFormat("Score: %d", finalScore);
        const char *yesMsg = "Y - Save";
        const char *noMsg  = "N / ESC - Skip";

        DrawText(msg, GetScreenWidth()/2 - MeasureText(msg, 40)/2, 150, 40, RAYWHITE);
        DrawText(scoreMsg, GetScreenWidth()/2 - MeasureText(scoreMsg, 30)/2, 220, 30, LIGHTGRAY);
        DrawText(yesMsg, GetScreenWidth()/2 - MeasureText(yesMsg, 24)/2, 310, 24, GREEN);
        DrawText(noMsg,  GetScreenWidth()/2 - MeasureText(noMsg,  24)/2, 350, 24, RED);

        EndDrawing();

        if (IsKeyPressed(KEY_Y)) return 1;
        if (IsKeyPressed(KEY_N) || IsKeyPressed(KEY_ESCAPE)) return 0;
    }
    return 0;
}

// Main "Game Over" screen, returns:
// 0 = quit, 1 = retry, 2 = return to menu
int showGameOverScreen(const char *playerName) {
    SetExitKey(KEY_NULL);
    while (!WindowShouldClose()) {
        BeginDrawing();
        ClearBackground(BLACK);

        const char *msg  = "GAME OVER";
        const char *sub1 = TextFormat("Player: %s", playerName);
        const char *sub2 = TextFormat("Final Score: %d", score);
        const char *opt1 = "R - Retry";
        const char *opt2 = "Q / ESC - Quit to Console";
        const char *opt3 = "E - Return to Main Menu";

        int font1 = 72;
        int textW = MeasureText(msg, font1);
        float t = GetTime();
        Color pulse = (Color){255, (int)(64 + 64 * sin(t * 3)),
                                   (int)(64 + 64 * sin(t * 3)), 255};

        DrawText(msg, GetScreenWidth()/2 - textW/2, GetScreenHeight()/2 - 150, font1, pulse);
        DrawText(sub1, GetScreenWidth()/2 - MeasureText(sub1, 26)/2, GetScreenHeight()/2 - 40, 26, RAYWHITE);
        DrawText(sub2, GetScreenWidth()/2 - MeasureText(sub2, 26)/2, GetScreenHeight()/2,     26, LIGHTGRAY);
        DrawText(opt1, GetScreenWidth()/2 - MeasureText(opt1, 20)/2, GetScreenHeight()/2 + 80, 20, LIGHTGRAY);
        DrawText(opt2, GetScreenWidth()/2 - MeasureText(opt2, 20)/2, GetScreenHeight()/2 + 110,20, LIGHTGRAY);
        DrawText(opt3, GetScreenWidth()/2 - MeasureText(opt3, 20)/2, GetScreenHeight()/2 + 140,20, LIGHTGRAY);

        EndDrawing();

        if (IsKeyPressed(KEY_R)) return 1;
        if (IsKeyPressed(KEY_E)) return 2;
        if (IsKeyPressed(KEY_Q) || IsKeyPressed(KEY_ESCAPE)) return 0;
    }
    return 0;
}

// Main game loop

// Full Tetris gameplay loop; returns only when game ends / player leaves
void playGame(Profile *player) {
    int winW, winH;

    resetGameState();

    double nextFall = GetTime() + timer_ms / 1000.0;
    double startTime = GetTime();
    int paused = 0;
    int shapeIndex = 0;

    while (GameOn && !WindowShouldClose()) {
        // Allow quitting mid-game
        if (IsKeyPressed(KEY_Q)) {
            GameOn = FALSE;
            break;
        }

        // Toggle pause
        if (IsKeyPressed(KEY_P)) {
            paused = !paused;
        }

        if (!paused) {
            // Left/right/rotate
            if (IsKeyPressed(KEY_A) || IsKeyDown(KEY_LEFT)) {
                (void)ManipulateCurrent('a', &shapeIndex);
            }
            if (IsKeyPressed(KEY_D) || IsKeyDown(KEY_RIGHT)) {
                (void)ManipulateCurrent('d', &shapeIndex);
            }
            if (IsKeyPressed(KEY_W) || IsKeyPressed(KEY_UP)) {
                (void)ManipulateCurrent('w', &shapeIndex);
            }

            // Hard drop: keep moving down until collision
            if (IsKeyPressed(KEY_SPACE)) {
                while (CheckPositionAt(current.array, current.width, current.row + 1, current.col)) {
                    current.row++;
                }
                WriteToTable();
                RemoveFullRowsAndUpdateScore();
                shapeIndex = dequeueShape();
                enqueueShape(rand() % 7);
                SetNewRandomShape(shapeIndex);
            }

            // Gravity
            double now = GetTime();
            double fallDelay = timer_ms / 1000.0;

            // Soft drop if S/down is held
            if (IsKeyDown(KEY_S) || IsKeyDown(KEY_DOWN)) {
                fallDelay = 0.06;
            }

            if (now >= nextFall) {
                if (!CheckPositionAt(current.array, current.width, current.row + 1, current.col)) {
                    // Lock piece if we can't go further down
                    WriteToTable();
                    RemoveFullRowsAndUpdateScore();
                    shapeIndex = dequeueShape();
                    enqueueShape(rand() % 7);
                    SetNewRandomShape(shapeIndex);
                } else {
                    current.row++;
                }
                nextFall = now + fallDelay;
            }

            // Dynamic difficulty: level increases with time and score
            double elapsed = GetTime() - startTime;
            int timeLevel  = (int)(elapsed / 30.0);
            int scoreLevel = score / 1000;
            level = (timeLevel > scoreLevel) ? timeLevel : scoreLevel;

            int new_timer = BASE_TIMER_MS - (level * 15);
            if (new_timer < MIN_TIMER_MS) new_timer = MIN_TIMER_MS;
            timer_ms = new_timer;
        }

        //  rendering

        winW = GetScreenWidth();
        winH = GetScreenHeight();

        // Board origin relative to window size
        GRID_X = (int)(winW * 0.10f);
        GRID_Y = (int)(winH * 0.10f);

        // Cell size adapts to window height
        CELL = (winH - GRID_Y - 40) / ROWS;
        if (CELL < 16) CELL = 16;
        if (CELL > 48) CELL = 48;

        BeginDrawing();
        ClearBackground((Color){20, 20, 20, 255});
        DrawRectangleGradientV(0, 0, winW, winH,
                               (Color){10,10,10,255}, (Color){35,35,35,255});

        // Pulse color for TETRIS title
        float t = GetTime();
        int r = (int)(128 + 127 * sin(t * 2.0));
        int g = (int)(128 + 127 * sin(t * 2.0 + 2.0));
        int b = (int)(128 + 127 * sin(t * 2.0 + 4.0));
        Color titleColor = (Color){r, g, b, 255};

        DrawText("TETRIS", GRID_X, 20, 32, titleColor);

        int elapsed = (int)(GetTime() - startTime);

        // Sidebar HUD (score, level, next, time)
        drawSidebar(player, elapsed);

        // Controls legend box
        float controlBoxX = winW * 0.70f - 15;
        float controlBoxY = winH * 0.60f;
        float controlBoxW = CELL * 10;
        float controlBoxH = CELL * 6;

        DrawRectangle(controlBoxX, controlBoxY, controlBoxW, controlBoxH,
                      Fade((Color){50,50,50,255}, 0.6f));
        DrawRectangleLines(controlBoxX, controlBoxY, controlBoxW, controlBoxH,
                           (Color){90,90,90,255});

        float textX = controlBoxX + 20;
        float textY = controlBoxY + 10;

        DrawText("Controls:", textX, textY, 16, RAYWHITE);
        textY += 25;

        DrawText("A/D or Left/Right : Move", textX, textY, 14, LIGHTGRAY);
        textY += 20;

        DrawText("S or Down         : Soft Drop", textX, textY, 14, LIGHTGRAY);
        textY += 20;

        DrawText("Space             : Hard Drop", textX, textY, 14, LIGHTGRAY);
        textY += 20;

        DrawText("W or Up           : Rotate", textX, textY, 14, LIGHTGRAY);
        textY += 20;

        DrawText("P: Pause   Q: Quit", textX, textY, 14, LIGHTGRAY);

        // Draw board and current falling piece
        drawGridAndCurrent();

        // Pause overlay
        if (paused) {
            DrawRectangle(0, 0, winW, winH, Fade(BLACK, 0.6f));
            const char *pauseText = "PAUSED";
            int fontSize = 64;
            int textWidth = MeasureText(pauseText, fontSize);
            int xx = winW/2 - textWidth/2;
            int yy = winH/2 - fontSize/2;
            DrawText(pauseText, xx, yy, fontSize, RAYWHITE);

            const char *resumeHint = "Press P to resume";
            int hintSize = 22;
            int hintWidth = MeasureText(resumeHint, hintSize);
            DrawText(resumeHint, winW/2 - hintWidth/2, yy + fontSize + 15, hintSize, LIGHTGRAY);
        }

        EndDrawing();

        if (!GameOn) break;
    }

    // Clean up shape memory and queue after leaving loop
    safe_free_shape(&current);
    freeQueue();

    // If window is still open, show Game Over + ask to save score
    if (!WindowShouldClose()) {
        int result = showGameOverScreen(player->name);
        int saveChoice = askSaveDataScreen(score);

        if (saveChoice == 1) {
            saveScore(player->name, score);
            player->timesPlayed++;

            if (score > player->bestScore)
                player->bestScore = score;

            double endTime = GetTime();
            int sessionTime = (int)(endTime - startTime);
            player->totalTime += sessionTime;

            saveProfiles();
        }

        if (result == 1) {   // Retry
            resetGameState();
            playGame(player);
            return;
        }

        if (result == 2) {   // return to menu
            return;
        }
    }
}
