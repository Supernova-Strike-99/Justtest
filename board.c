//   board.c - prints the grid, sidebar and basic UI widgets

#include "tetris.h"

// Shared text input buffer for all name/input dialogues
char inputBuffer[50];

// ui helpers

// heading(RGB) that changes colour
Color neonPulse() {
    float t = GetTime();
    int r = (int)(128 + 127 * sin(t * 2.0));
    int g = (int)(128 + 127 * sin(t * 2.0 + 2.0));
    int b = (int)(128 + 127 * sin(t * 2.0 + 4.0));
    return (Color){r, g, b, 255};
}

// check if the button has just been clicked
int ButtonClicked(Button b) {
    Vector2 m = GetMousePosition();
    return CheckCollisionPointRec(m, b.rect) && IsMouseButtonPressed(MOUSE_LEFT_BUTTON);
}

// drawing button with neon hover effect
void DrawButtonTheme(Button b) {
    Vector2 m = GetMousePosition();
    int hover = CheckCollisionPointRec(m, b.rect);

    Color border = hover ? neonPulse() : (Color){90,90,90,255};
    Color fill   = hover ? (Color){50,50,50,255} : (Color){30,30,30,255};

    DrawRectangleRec(b.rect, fill);
    DrawRectangleLinesEx(b.rect, 2, border);

    int w = MeasureText(b.label, 22);
    DrawText(b.label, b.rect.x + b.rect.width/2 - w/2, b.rect.y + 8, 22, RAYWHITE);
}

// back button at the bottom left,when clicked 1 is returned
int DrawBackButton() {
    Button backBtn = (Button){ { 40, GetScreenHeight() - 80, 160, 40 }, "Back" };
    DrawButtonTheme(backBtn);
    if (ButtonClicked(backBtn)) return 1;
    return 0;
}

// input box

// simple blocking text input dialog. Returns 1 on OK,returns 0 on back
int themedInputBox(const char *prompt) {
    SetExitKey(KEY_NULL);
    memset(inputBuffer, 0, sizeof(inputBuffer));

    while (1) {
        int w = GetScreenWidth();
        int h = GetScreenHeight();

        BeginDrawing();
        ClearBackground((Color){15,15,15,255});
        DrawRectangleGradientV(0,0,w,h,(Color){10,10,10,255},(Color){40,40,40,255});

        Color pulse = neonPulse();

        int pw = MeasureText(prompt, 34);
        DrawText(prompt, w/2 - pw/2, h/3 - 40, 34, pulse);

        Rectangle box = {
            w * 0.20f,
            h * 0.45f,
            w * 0.60f,
            h * 0.08f
        };

        DrawRectangleRec(box, (Color){40,40,40,255});
        DrawRectangleLinesEx(box, 2, pulse);

        DrawText(inputBuffer, box.x + 10, box.y + 12, 26, RAYWHITE);

        const char *hint = "ENTER = OK   ESC = Back";
        int hw = MeasureText(hint, 20);
        DrawText(hint, w/2 - hw/2, box.y + box.height * 0.65f, 20, LIGHTGRAY);

        EndDrawing();

        // Basic backspace handling
        if (IsKeyPressed(KEY_BACKSPACE) && strlen(inputBuffer) > 0)
            inputBuffer[strlen(inputBuffer)-1] = 0;

        // Append printable characters to buffer
        int c = GetCharPressed();
        if (c >= 32 && c <= 126 && strlen(inputBuffer) < 49)
            inputBuffer[strlen(inputBuffer)] = (char)c;

        // Confirm / cancel
        if (IsKeyPressed(KEY_ENTER)) return 1;
        if (IsKeyPressed(KEY_ESCAPE)) return 0;
    }
}

// board drawing 

// Draw the main Tetris grid and the current falling shape
void drawGridAndCurrent(void) {
    char Buffer[ROWS][COLS]; 
    memset(Buffer, 0, sizeof(Buffer));
    memcpy(Buffer, Table, sizeof(Table));

    // Overlay current piece into temporary buffer
    if (current.array)
        for (int i = 0; i < current.width; ++i)
            for (int j = 0; j < current.width; ++j)
                if (current.array[i][j]) {
                    int r = current.row + i, c = current.col + j;
                    if (r >= 0 && r < ROWS && c >= 0 && c < COLS) Buffer[r][c] = 1;
                }

    // Draw all cells
    for (int r = 0; r < ROWS; ++r) {
        for (int c = 0; c < COLS; ++c) {
            Rectangle rect = { (float)(GRID_X + c * CELL), (float)(GRID_Y + r * CELL),
                               (float)(CELL - 2), (float)(CELL - 2) };
            DrawRectangleRec(rect, Buffer[r][c] ? SKYBLUE : (Color){40, 40, 40, 255});
            DrawRectangleLines((int)rect.x, (int)rect.y,
                               (int)rect.width, (int)rect.height,
                               (Color){60, 60, 60, 255});
        }
    }
}

// Small preview of the next block in the sidebox
void drawNextPreview(int px, int py) {
    int next = peekNextShape();
    int w = ShapeWidths[next];
    const signed char *src = NULL;

    // Pick the correct constant shape array
    switch (next) {
        case 0: src = &S0_0[0][0]; break;
        case 1: src = &S1_0[0][0]; break;
        case 2: src = &S2_0[0][0]; break;
        case 3: src = &S3_0[0][0]; break;
        case 4: src = &S4_0[0][0]; break;
        case 5: src = &S5_0[0][0]; break;
        case 6: src = &S6_0[0][0]; break;
    }

    DrawRectangle(px - 6, py - 6, w * CELL + 12, w * CELL + 12, FOG);

    for (int i = 0; i < w; ++i) {
        for (int j = 0; j < w; ++j) {
            Rectangle r = { (float)(px + j * CELL), (float)(py + i * CELL),
                            (float)(CELL - 2), (float)(CELL - 2) };
            DrawRectangleRec(r, src[i * w + j] ? ORANGE : LIGHTGRAY);
            DrawRectangleLines((int)r.x, (int)r.y, (int)r.width, (int)r.height, BLACK);
        }
    }
}

// Draw score, level, time, next piece etc. on the right side
void drawSidebar(Profile *player, int elapsed) {
    float winW = GetScreenWidth();
    float winH = GetScreenHeight();

    float sidebarX = winW * 0.70f;
    float sidebarY = winH * 0.10f;

    float y = sidebarY;

    DrawText(TextFormat("Player: %s", player->name), sidebarX, y, 18, LIGHTGRAY);
    y += 40;

    DrawText(TextFormat("Score: %d", score), sidebarX, y, 22, RAYWHITE);
    y += 40;

    DrawText(TextFormat("Level: %d", level), sidebarX, y, 18, LIGHTGRAY);
    y += 40;

    DrawText(TextFormat("Gravity: %d ms", timer_ms), sidebarX, y, 18, LIGHTGRAY);
    y += 40;

    DrawText(TextFormat("Time: %02d:%02d", elapsed/60, elapsed%60), sidebarX, y, 18, LIGHTGRAY);
    y += 40;

    DrawText("Next:", sidebarX, y, 20, DARKGRAY);
    y += 30;

    drawNextPreview((int)(sidebarX + CELL), (int)y);
}
