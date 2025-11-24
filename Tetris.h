// Tetris.h - shared declarations for Tetris project

#ifndef TETRIS_H
#define TETRIS_H

#include "raylib.h"
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <ctype.h>

// Fog overlay color for next-piece preview
#define FOG (Color){ 100, 100, 100, 100 } // semi-transparent gray fog

// Basic board + game constants
#define ROWS 20
#define COLS 15
#define TRUE 1
#define FALSE 0
#define SCORE_FILE "scores.txt"
#define MAX_PLAYERS 200
#define MIN_TIMER_MS 50
#define BASE_TIMER_MS 400
#define PROFILE_DB "playerdb.txt"

// Single player's persistent stats
typedef struct Profile {
    char name[50];
    int timesPlayed;
    int bestScore;
    int totalTime;  // total play time in seconds
    struct Profile *next;
} Profile;

// A single falling Tetris piece
typedef struct {
    char **array;   // dynamically allocated square matrix
    int width;      // size of that matrix (2,3,4)
    int row, col;   // position on the board
} Shape;

// One row of high score data
typedef struct {
    char name[50];
    int score;
} Player;

// Queue node for upcoming shapes
typedef struct Node {
    int shapeIndex;
    struct Node *next;
} Node;

// Simple clickable button
typedef struct {
    Rectangle rect;
    const char *label;
} Button;

// Context menu state for profile list
typedef struct {
    int open;
    int index;
    int x, y;
} PopupMenu;

// Globals ( the ones which are defined in .c files )
extern int CELL;
extern int GRID_X;
extern int GRID_Y;

extern char Table[ROWS][COLS];
extern int score;
extern int GameOn;
extern int timer_ms;
extern int level;

extern Profile *profileHead;
extern Profile *currentPlayer;

extern Node *head;
extern Node *tail;

extern PopupMenu popup;
extern Shape current;

// shape data thats defined in game_logic.c
extern const signed char S0_0[3][3];
extern const signed char S1_0[3][3];
extern const signed char S2_0[3][3];
extern const signed char S3_0[3][3];
extern const signed char S4_0[3][3];
extern const signed char S5_0[2][2];
extern const signed char S6_0[4][4];
extern const int ShapeWidths[7];

//  shared input buffer for name input in board.c
extern char inputBuffer[50];

// UI helpers/ board.c
Color neonPulse(void);

int ButtonClicked(Button b);
void DrawButtonTheme(Button b);
int DrawBackButton(void);
int themedInputBox(const char *prompt);

void drawGridAndCurrent(void);
void drawNextPreview(int px, int py);
void drawSidebar(Profile *player, int elapsed);

// Game logic / game_logic.c
void enqueueShape(int shapeIndex);
int dequeueShape(void);
int peekNextShape(void);
void freeQueue(void);

void safe_free_shape(Shape *s);
Shape make_copy_from_constshape(int index);

int CheckPositionAt(char **array, int width, int row, int col);
int CheckPositionBuf(char buf[4][4], int width, int row, int col);
void make_rotated_buffer(char buf[4][4], char **src, int width);
void apply_rotated_to_current(char buf[4][4], int width);

void SetNewRandomShape(int shapeIndex);
void RemoveFullRowsAndUpdateScore(void);
void WriteToTable(void);
void RotateCurrentIfPossible(void);
int ManipulateCurrent(int action, int *shapeIndex);

int askSaveDataScreen(int finalScore);
int showGameOverScreen(const char *playerName);

void resetGameState(void);
void playGame(Profile *player);

// File management / file_manager.c
void showScores(void);
void clearScores(void);
void saveScore(const char *name, int score_v);

void loadProfiles(void);
void saveProfiles(void);
Profile* searchProfileByName(const char *name);

Profile* getPlayerFromGUI(void);

void addProfile_GUI(void);
void searchProfile_GUI(void);
void updateProfile_GUI(void);
void deleteProfile_GUI(void);
void deleteAllProfiles_GUI(void);
void listProfiles_GUI(void);
void showScores_GUI(void);
void drawProfilePopup(Profile *pr);
void playerManagerMenu_GUI(void);


#endif 