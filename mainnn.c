#include "tetris.h"

// Simple helper to clear any leftover characters from stdin.
static void flush_stdin(void) {
    int ch;
    while ((ch = getchar()) != '\n' && ch != EOF) {}
}

// Main GUI menu for the game.
// Returns:
//   1 - New Game
//   2 - Player Manager
//   3 - Quit
int mainMenu_GUI(Profile *player) {
    (void)player; // player not used directly here in the menu
    SetExitKey(KEY_NULL);
    SetTargetFPS(144);

    while (!WindowShouldClose()) {
        int w = GetScreenWidth();
        int h = GetScreenHeight();
        float bw = w * 0.30f;
        float bh = h * 0.08f;
        float cx = w * 0.50f - bw/2;

        Button newGame = {{cx, h*0.34f, bw, bh}, "New Game"};
        Button manage  = {{cx, h*0.48f, bw, bh}, "Player Manager"};
        Button quit    = {{cx, h*0.62f, bw, bh}, "Quit"};

        BeginDrawing();
        ClearBackground((Color){15,15,15,255});
        DrawRectangleGradientV(0,0,w,h,(Color){10,10,10,255},(Color){40,40,40,255});

        Color pulse = neonPulse();
        const char *title = "TETRIS MENU";
        int tw = MeasureText(title, 42);
        DrawText(title, w/2 - tw/2, 60, 42, pulse);

        DrawButtonTheme(newGame);
        DrawButtonTheme(manage);
        DrawButtonTheme(quit);

        EndDrawing();

        // Menu selection
        if (ButtonClicked(newGame)) return 1;
        if (ButtonClicked(manage))  return 2;
        if (ButtonClicked(quit))    return 3;
    }

    // If window is closed from the OS, treat it as "Quit"
    return 3;
}

int main(void) {
    // Disable stdout buffering (useful for debugging prints).
    setvbuf(stdout, NULL, _IONBF, 0);

    // Seed RNG for random shapes.
    srand((unsigned)time(NULL));

    // Load player profiles from disk before opening the window.
    loadProfiles();

    // Allow the window to be resized while playing.
    SetConfigFlags(FLAG_WINDOW_RESIZABLE);

    InitWindow(1000, 800, "Tetris");
    SetTargetFPS(144);

    // Ask the user to choose/create a profile before entering the main menu.
    currentPlayer = getPlayerFromGUI();
    if (!currentPlayer) {
        // User cancelled or closed the window in the name prompt.
        CloseWindow();
        return 0;
    }

    // Main application loop. shows menu, then handles the chosen action.
    while (!WindowShouldClose()) {
        int choice = mainMenu_GUI(currentPlayer);

        switch (choice) {
            case 1: // New Game
                playGame(currentPlayer);
                break;
            case 2: // Player Manager
                playerManagerMenu_GUI();
                break;
            case 3: // Quit
                CloseWindow();
                return 0;
            default:
                break;
        }
    }

    CloseWindow();
    return 0;
}
