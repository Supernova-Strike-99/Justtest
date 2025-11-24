// file_manager.c - profiles, scores and related GUI screens

#include "tetris.h"

// profile globals

Profile *profileHead = NULL;     // Linked list head
Profile *currentPlayer = NULL;   // Currently active player profile

PopupMenu popup = {0, -1, 0, 0};
static int selectedProfileIndex = -1;

// score file helpers

// Load all scores from disk into the given array, return count
static int load_all_scores(Player *players, int max) {
    FILE *f = fopen(SCORE_FILE, "r");
    if (!f) return 0;

    int count = 0;
    while (count < max && fscanf(f, "%49s %d", players[count].name, &players[count].score) == 2)
        count++;

    fclose(f);
    return count;
}

// Sort players by score in descending order
static int compare_players_desc(const void *a, const void *b) {
    const Player *pa = (const Player *)a;
    const Player *pb = (const Player *)b;
    return pb->score - pa->score;
}

// Rewrite score file from array (already sorted by score)
static void save_all_scores(Player *players, int count) {
    if (count > 1) qsort(players, count, sizeof(Player), compare_players_desc);

    FILE *f = fopen(SCORE_FILE, "w");
    if (!f) return;

    for (int i = 0; i < count; ++i)
        fprintf(f, "%s %d\n", players[i].name, players[i].score);

    fclose(f);
}

// public score API

// Save a score for a player, keeping only the best score per name (case-insensitive)
void saveScore(const char *name, int score_v) {
    Player players[MAX_PLAYERS];
    int count = load_all_scores(players, MAX_PLAYERS);
    int found = 0;

    char loweredName[50];
    strncpy(loweredName, name, 49);
    loweredName[49] = '\0';
    for (int i = 0; loweredName[i]; i++)
        loweredName[i] = (char)tolower((unsigned char)loweredName[i]);

    // Match existing entry ignoring case
    for (int i = 0; i < count; ++i) {
        char storedLower[50];
        strncpy(storedLower, players[i].name, 49);
        storedLower[49] = '\0';

        for (int j = 0; storedLower[j]; j++)
            storedLower[j] = (char)tolower((unsigned char)storedLower[j]);

        if (strcmp(storedLower, loweredName) == 0) {
            if (score_v > players[i].score) players[i].score = score_v;
            found = 1;
            break;
        }
    }

    if (!found && count < MAX_PLAYERS) {
        strncpy(players[count].name, name, 49);
        players[count].name[49] = '\0';
        players[count].score = score_v;
        count++;
    }

    if (count > 1) qsort(players, count, sizeof(Player), compare_players_desc);

    FILE *f = fopen(SCORE_FILE, "w");
    if (!f) return;

    for (int i = 0; i < count; ++i)
        fprintf(f, "%s %d\n", players[i].name, players[i].score);

    fclose(f);
}

// console-only high score view (mainly debugging / fallback)
void showScores(void) {
    FILE *f = fopen(SCORE_FILE, "r");
    if (!f) {
        printf("No high scores yet.\n");
        return;
    }

    printf("\n=== HIGH SCORES ===\n");
    char name[50];
    int s;
    int rank = 1;

    while (fscanf(f, "%49s %d", name, &s) == 2) {
        printf("%2d. %-20s %6d\n", rank++, name, s);
    }

    fclose(f);
    printf("===================\n");
}

// Delete score file completely
void clearScores(void) {
    remove(SCORE_FILE);
    printf("All scores deleted.\n");
}

// load/save profile

// Load all profiles from disk into a linked list
void loadProfiles() {
    FILE *f = fopen(PROFILE_DB, "r");
    if (!f) return;

    Profile temp;
    temp.totalTime = 0;

    while (fscanf(f, "%49s %d %d %d",
                  temp.name, &temp.timesPlayed, &temp.bestScore, &temp.totalTime) == 4)
    {
        Profile *node = (Profile *)malloc(sizeof(Profile));
        *node = temp;
        node->next = profileHead;
        profileHead = node;
    }

    fclose(f);
}

// Write all profiles in the current linked list to disk
void saveProfiles() {
    FILE *f = fopen(PROFILE_DB, "w");
    if (!f) return;

    Profile *p = profileHead;
    while (p) {
        fprintf(f, "%s %d %d %d\n", p->name, p->timesPlayed, p->bestScore, p->totalTime);
        p = p->next;
    }

    fclose(f);
}

//profile search

// Linear search by exact name
Profile* searchProfileByName(const char *name) {
    Profile *p = profileHead;
    while (p) {
        if (strcmp(p->name, name) == 0) return p;
        p = p->next;
    }
    return NULL;
}

// player input/creation

// Ask for a player using the GUI. creates profile if it doesn't exist
Profile* getPlayerFromGUI() {
    SetExitKey(KEY_NULL);
    while (!WindowShouldClose()) {
        if (!themedInputBox("Enter Player Name:")) return NULL;

        if (strlen(inputBuffer) == 0)
            continue;

        // If profile exists, reuse it
        Profile *p = searchProfileByName(inputBuffer);
        if (p) {
            currentPlayer = p;
            return p;
        }

        // else create a new one
        Profile *np = (Profile *)malloc(sizeof(Profile));
        strncpy(np->name, inputBuffer, 49);
        np->name[49] = 0;
        np->timesPlayed = 0;
        np->bestScore = 0;
        np->next = profileHead;
        profileHead = np;
        np->totalTime = 0;

        saveProfiles();
        currentPlayer = np;

        return np;
    }
    return NULL;
}

// profile crud GUI

// Add a new profile from a GUI prompt
void addProfile_GUI() {
    SetExitKey(KEY_NULL);
    while (1) {
        if (!themedInputBox("Enter Player Name:")) return;
        if (strlen(inputBuffer) == 0) return;
        break;
    }

    Profile *p = (Profile *)malloc(sizeof(Profile));

    strncpy(p->name, inputBuffer, 49);
    p->name[49] = 0;

    p->timesPlayed = 0;
    p->bestScore = 0;
    p->totalTime = 0;

    p->next = profileHead;
    profileHead = p;

    saveProfiles();
}

// Show a single profile's details in a modal screen
void searchProfile_GUI() {
    SetExitKey(KEY_NULL);
    if (!themedInputBox("Search Player:")) return;

    Profile *p = searchProfileByName(inputBuffer);

    while (1) {
        int w = GetScreenWidth();
        int h = GetScreenHeight();

        BeginDrawing();
        ClearBackground((Color){15,15,15,255});
        DrawRectangleGradientV(0,0,w,h,(Color){10,10,10,255},(Color){40,40,40,255});

        Color pulse = neonPulse();

        const char *title = "SEARCH RESULT";
        int tw = MeasureText(title, 36);
        DrawText(title, w/2 - tw/2, 60, 36, pulse);

        float boxW = w * 0.50f;
        float boxH = h * 0.22f;
        float boxX = w/2 - boxW/2;
        float boxY = h/2 - boxH/2;

        DrawRectangle(boxX, boxY, boxW, boxH, (Color){40,40,40,180});
        DrawRectangleLines(boxX, boxY, boxW, boxH, pulse);

        float tx = boxX + 20;
        float ty = boxY + 20;

        if (!p) {
            DrawText("NOT FOUND", tx, ty, 32, RED);
        } else {
            DrawText(TextFormat("Name: %s", p->name), tx, ty, 26, RAYWHITE);
            ty += 30;
            DrawText(TextFormat("Times Played: %d", p->timesPlayed), tx, ty, 22, LIGHTGRAY);
            ty += 30;
            DrawText(TextFormat("Best Score: %d", p->bestScore), tx, ty, 22, LIGHTGRAY);
            ty += 30;
            DrawText(TextFormat("Total Time: %02d:%02d", p->totalTime/60, p->totalTime%60),
                     tx, ty, 22, LIGHTGRAY);
        }

        if (DrawBackButton()) return;

        EndDrawing();
    }
}

// Update an existing profile's name
void updateProfile_GUI() {
    SetExitKey(KEY_NULL);
    if (!themedInputBox("Enter Old Name:")) return;

    Profile *p = searchProfileByName(inputBuffer);
    if (!p) return;

    if (!themedInputBox("Enter New Name:")) return;

    strncpy(p->name, inputBuffer, 49);
    p->name[49] = 0;

    saveProfiles();

    // Simple confirmation box
    while (1) {
        int w = GetScreenWidth();
        int h = GetScreenHeight();
        Color pulse = neonPulse();

        BeginDrawing();
        ClearBackground((Color){15,15,15,255});
        DrawRectangleGradientV(0,0,GetScreenWidth(),GetScreenHeight(),
                               (Color){10,10,10,255},(Color){40,40,40,255});

        float boxW = w * 0.40f;
        float boxH = h * 0.15f;
        float boxX = w/2 - boxW/2;
        float boxY = h/2 - boxH/2;

        DrawRectangle(boxX, boxY, boxW, boxH, (Color){40,40,40,180});
        DrawRectangleLines(boxX, boxY, boxW, boxH, pulse);

        float tx = boxX + 20;
        float ty = boxY + 30;
        DrawText("Profile Updated!", tx, ty, 32, RAYWHITE);

        if (DrawBackButton()) return;

        EndDrawing();
    }
}

// Delete a single profile by name
void deleteProfile_GUI() {
    SetExitKey(KEY_NULL);
    if (!themedInputBox("Delete Player:")) return;

    Profile *prev = NULL;
    Profile *curr = profileHead;
    int deleted = 0;

    while (curr) {
        if (strcmp(curr->name, inputBuffer) == 0) {
            if (!prev) profileHead = curr->next;
            else prev->next = curr->next;

            free(curr);
            saveProfiles();
            deleted = 1;
            break;
        }
        prev = curr;
        curr = curr->next;
    }

    // Feedback screen: deleted vs not-found
    while (1) {
        int w = GetScreenWidth();
        int h = GetScreenHeight();
        Color pulse = neonPulse();

        BeginDrawing();
        ClearBackground((Color){15,15,15,255});
        DrawRectangleGradientV(0,0,GetScreenWidth(),GetScreenHeight(),
                               (Color){10,10,10,255},(Color){40,40,40,255});

        float boxW = w * 0.40f;
        float boxH = h * 0.15f;
        float boxX = w/2 - boxW/2;
        float boxY = h/2 - boxH/2;

        DrawRectangle(boxX, boxY, boxW, boxH, (Color){40,40,40,180});
        DrawRectangleLines(boxX, boxY, boxW, boxH, pulse);

        float tx = boxX + 20;
        float ty = boxY + 30;

        if (deleted)
            DrawText("Profile Deleted!", tx, ty, 32, RED);
        else
            DrawText("Profile Not Found", tx, ty, 32, RAYWHITE);

        if (DrawBackButton()) return;

        EndDrawing();
    }
}

// delete all profiles

// Sort helper for listing profiles by bestScore
static int compareProfilesDesc(const void *a, const void *b) {
    Profile *pa = *(Profile**)a;
    Profile *pb = *(Profile**)b;
    return pb->bestScore - pa->bestScore;
}

// Confirmation + delete everything from memory and disk
void deleteAllProfiles_GUI() {
    SetExitKey(KEY_NULL);

    // Confirmation loop
    while (1) {
        int w = GetScreenWidth();
        int h = GetScreenHeight();
        Color pulse = neonPulse();

        BeginDrawing();
        ClearBackground((Color){15,15,15,255});
        DrawRectangleGradientV(0,0,w,h,(Color){10,10,10,255},(Color){40,40,40,255});

        const char *msg = "Delete ALL profiles?";
        const char *warn = "This cannot be undone.";
        const char *optYes = "Y - Confirm";
        const char *optNo  = "N / Back";

        DrawText(msg,  w/2 - MeasureText(msg,  36)/2, h/3,     36, RED);
        DrawText(warn, w/2 - MeasureText(warn, 24)/2, h/3 +40, 24, LIGHTGRAY);
        DrawText(optYes,w/2 - MeasureText(optYes,24)/2, h/3+120,24, GREEN);
        DrawText(optNo, w/2 - MeasureText(optNo, 24)/2, h/3+160,24, RAYWHITE);

        EndDrawing();

        if (IsKeyPressed(KEY_Y)) break;
        if (IsKeyPressed(KEY_N) || IsKeyPressed(KEY_ESCAPE)) return;
    }

    // Free linked list in memory
    Profile *p = profileHead;
    while (p) {
        Profile *temp = p;
        p = p->next;
        free(temp);
    }
    profileHead = NULL;

    remove(PROFILE_DB);

    // Show final "deleted" message
    while (1) {
        int w = GetScreenWidth();
        int h = GetScreenHeight();
        Color pulse = neonPulse();

        BeginDrawing();
        ClearBackground((Color){15,15,15,255});
        DrawRectangleGradientV(0,0,w,h,(Color){10,10,10,255},(Color){40,40,40,255});

        const char *msg = "All Profiles Deleted!";
        DrawText(msg, w/2 - MeasureText(msg, 32)/2, h/2 - 20, 32, RED);

        if (DrawBackButton()) return;

        EndDrawing();
    }
}

// popup and list profiles

// Right-click popup menu for a single profile row
void drawProfilePopup(Profile *pr) {
    int w = GetScreenWidth();
    int h = GetScreenHeight();

    int boxW = 260;
    int boxH = 140;

    int x = popup.x;
    int y = popup.y;

    // Clamp popup inside window
    if (x + boxW > w) x = w - boxW - 10;
    if (y + boxH > h) y = h - boxH - 10;

    Rectangle box = (Rectangle){ x, y, boxW, boxH };

    DrawRectangleRec(box, (Color){30,30,30,240});
    DrawRectangleLinesEx(box, 2, neonPulse());

    DrawText("Profile Options", x + 10, y + 10, 22, RAYWHITE);

    Button btnEdit   = (Button){ { x + 20, y + 50, boxW - 40, 30 }, "Edit Name" };
    Button btnDelete = (Button){ { x + 20, y + 90, boxW - 40, 30 }, "Delete Profile" };

    DrawButtonTheme(btnEdit);
    DrawButtonTheme(btnDelete);

    // Rename profile from popup
    if (ButtonClicked(btnEdit)) {
        popup.open = 0;

        if (themedInputBox("Enter New Name:")) {
            strncpy(pr->name, inputBuffer, 49);
            pr->name[49] = 0;
            saveProfiles();
        }
    }

    // Delete profile from popup
    if (ButtonClicked(btnDelete)) {
        popup.open = 0;

        Profile *prev = NULL, *cur = profileHead;
        while (cur) {
            if (cur == pr) {
                if (prev) prev->next = cur->next;
                else profileHead = cur->next;
                free(cur);
                saveProfiles();
                popup.index = -999; // signal that list needs refresh
                return;
            }
            prev = cur;
            cur = cur->next;
        }
    }
}

// Table-style listing of all profiles, sortable and scrollable
void listProfiles_GUI() {
    SetExitKey(KEY_NULL);
    int scroll = 0;

    // Count profiles first
    int count = 0;
    Profile *p = profileHead;
    while (p) { count++; p = p->next; }

    // No profiles case
    if (count == 0) {
        while (1) {
            BeginDrawing();
            ClearBackground((Color){20,20,20,255});
            DrawText("No Profiles Found", 50, 50, 28, RED);
            if (DrawBackButton()) return;
            EndDrawing();
        }
    }

    // Build array of pointers so we can qsort by bestScore
    Profile **arr = (Profile **)malloc(sizeof(Profile*) * count);
    p = profileHead;
    for (int i = 0; i < count; i++) {
        arr[i] = p;
        p = p->next;
    }

    qsort(arr, count, sizeof(Profile*), compareProfilesDesc);

    while (1) {
        int w = GetScreenWidth();
        int h = GetScreenHeight();

        int tableX = (int)(w * 0.08f);
        int tableW = (int)(w * 0.84f);
        int rowH   = 44;

        int colNameW  = (int)(tableW * 0.32f);
        int colPlayW  = (int)(tableW * 0.16f);
        int colBestW  = (int)(tableW * 0.22f);
        int colTimeW  = (int)(tableW * 0.30f);

        BeginDrawing();
        ClearBackground((Color){15,15,15,255});
        DrawRectangleGradientV(0,0,w,h,(Color){10,10,10,255},(Color){40,40,40,255});

        Color pulse = neonPulse();
        DrawText("PLAYER PROFILES", w/2 - MeasureText("PLAYER PROFILES", 42)/2, 30, 42, pulse);

        int y = 120 + scroll;

        // Header row
        DrawRectangle(tableX, y, tableW, rowH, (Color){35,35,35,255});
        DrawRectangleLines(tableX, y, tableW, rowH, pulse);

        DrawText("Name",        tableX + 10,              y + 10, 22, RAYWHITE);
        DrawText("Played",      tableX + colNameW + 10,   y + 10, 22, RAYWHITE);
        DrawText("Best Score",  tableX + colNameW + colPlayW + 10, y + 10, 22, RAYWHITE);
        DrawText("Total Time",  tableX + colNameW + colPlayW + colBestW + 10, y + 10, 22, RAYWHITE);

        y += rowH;

        Vector2 m = GetMousePosition();

        // Draw each profile row
        for (int i = 0; i < count; i++) {
            Profile *pr = arr[i];

            Rectangle rowRect = (Rectangle){ tableX, (float)y, tableW, rowH };

            int hover = CheckCollisionPointRec(m, rowRect);
            int selected = (i == selectedProfileIndex);

            Color bg = (i % 2 == 0) ? (Color){30,30,30,220} : (Color){40,40,40,220};
            if (hover) bg = (Color){60,60,60,240};
            if (selected) bg = (Color){80,20,20,240};

            DrawRectangleRec(rowRect, bg);
            DrawRectangleLines(tableX, y, tableW, rowH, (Color){70,70,70,255});

            DrawText(pr->name, tableX + 10, y + 12, 20, RAYWHITE);
            DrawText(TextFormat("%d", pr->timesPlayed),
                     tableX + colNameW + 10, y + 12, 20, LIGHTGRAY);
            DrawText(TextFormat("%d", pr->bestScore),
                     tableX + colNameW + colPlayW + 10, y + 12, 20, LIGHTGRAY);
            DrawText(TextFormat("%02d:%02d", pr->totalTime/60, pr->totalTime%60),
                     tableX + colNameW + colPlayW + colBestW + 10, y + 12, 20, LIGHTGRAY);

            if (hover && IsMouseButtonPressed(MOUSE_LEFT_BUTTON)) {
                selectedProfileIndex = i;
            }

            // Right-click opens context menu for that row
            if (hover && IsMouseButtonPressed(MOUSE_RIGHT_BUTTON)) {
                popup.open = 1;
                popup.index = i;
                popup.x = (int)m.x;
                popup.y = (int)m.y;
            }

            y += rowH;
        }

        // Mouse wheel scrolling
        scroll += (int)(GetMouseWheelMove() * -20);

        // Draw popup if active
        if (popup.open && popup.index >= 0 && popup.index < count) {
            drawProfilePopup(arr[popup.index]);
        }
        // If popup deleted a profile, reload array
        if (popup.index == -999) {
            popup.index = -1;

            free(arr);

            count = 0;
            p = profileHead;
            while (p) { count++; p = p->next; }

            if (count == 0) return;

            arr = (Profile **)malloc(sizeof(Profile*) * count);
            p = profileHead;
            for (int i = 0; i < count; i++) {
                arr[i] = p;
                p = p->next;
            }

            qsort(arr, count, sizeof(Profile*), compareProfilesDesc);
        }

        if (DrawBackButton()) break;

        EndDrawing();
    }

    popup.open = 0;
    popup.index = -1;

    free(arr);
}

// high-scores GUI

// Simple high-score screen to show all scores scrolled vertically
void showScores_GUI() {
    Player p[MAX_PLAYERS];
    int count = load_all_scores(p, MAX_PLAYERS);

    SetExitKey(KEY_NULL);
    int scroll = 0;

    while (!WindowShouldClose()) {
        int w = GetScreenWidth();
        int h = GetScreenHeight();

        BeginDrawing();
        ClearBackground((Color){15,15,15,255});
        DrawRectangleGradientV(0,0,w,h,(Color){10,10,10,255},(Color){40,40,40,255});

        Color pulse = neonPulse();
        const char *title = "HIGH SCORES";
        int tw = MeasureText(title, 36);
        DrawText(title, w/2 - tw/2, 40, 36, pulse);

        int y = 120 + scroll;

        for (int i = 0; i < count; ++i) {
            DrawText(
                TextFormat("%d) %s   -   %d", i+1, p[i].name, p[i].score),
                w/2 - 250, y, 24, RAYWHITE
            );
            y += 35;
        }

        scroll += (int)(GetMouseWheelMove() * -20);

        if (DrawBackButton()) return;

        EndDrawing();
    }
}

// Player Manager Menu

// Main "Player Manager" menu hub
void playerManagerMenu_GUI(void) {
    SetExitKey(KEY_NULL);
    SetTargetFPS(144);

    while (!WindowShouldClose()) {
        int w = GetScreenWidth();
        int h = GetScreenHeight();
        float bw = w * 0.30f;
        float bh = h * 0.07f;
        float cx = w * 0.50f - bw/2;

        Button addBtn       = (Button){{ cx, h * 0.30f, bw, bh }, "Add Profile" };
        Button searchBtn    = (Button){{ cx, h * 0.40f, bw, bh }, "Search Profile" };
        Button updateBtn    = (Button){{ cx, h * 0.50f, bw, bh }, "Update Profile" };
        Button deleteBtn    = (Button){{ cx, h * 0.60f, bw, bh }, "Delete Profile" };
        Button deleteAllBtn = (Button){{ cx, h * 0.70f, bw, bh }, "Delete ALL Profiles" };
        Button listBtn      = (Button){{ cx, h * 0.80f, bw, bh }, "List All Profiles" };
        Button backBtn      = (Button){{ cx, h * 0.90f, bw, bh }, "Back" };

        BeginDrawing();
        ClearBackground((Color){15,15,15,255});
        DrawRectangleGradientV(0,0,w,h,(Color){10,10,10,255},(Color){40,40,40,255});

        Color pulse = neonPulse();
        const char *title = "PLAYER MANAGER";
        int tw = MeasureText(title, 38);
        DrawText(title, w/2 - tw/2, 60, 38, pulse);

        DrawButtonTheme(addBtn);
        DrawButtonTheme(searchBtn);
        DrawButtonTheme(updateBtn);
        DrawButtonTheme(deleteBtn);
        DrawButtonTheme(deleteAllBtn);
        DrawButtonTheme(listBtn);
        DrawButtonTheme(backBtn);

        EndDrawing();

        // Dispatch button actions
        if (ButtonClicked(addBtn))        addProfile_GUI();
        if (ButtonClicked(searchBtn))     searchProfile_GUI();
        if (ButtonClicked(updateBtn))     updateProfile_GUI();
        if (ButtonClicked(deleteBtn))     deleteProfile_GUI();
        if (ButtonClicked(deleteAllBtn))  deleteAllProfiles_GUI();
        if (ButtonClicked(listBtn))       listProfiles_GUI();
        if (ButtonClicked(backBtn))       return;
    }
}
