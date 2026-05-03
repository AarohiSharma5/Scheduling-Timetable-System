#include <iostream>
#include <vector>
#include <algorithm>
#include <queue>
#include <string>
#include <iomanip>
#include <climits>
#include <numeric>
#include <cstdio>
#include <map>
using namespace std;

// ============================================================================
//                        COMPETITIVE PROGRAMMING MACROS
// ============================================================================
#define fastio ios_base::sync_with_stdio(false); cin.tie(NULL)
#define ll long long
#define pb push_back
#define all(x) (x).begin(), (x).end()
#define sz(x) (int)((x).size())
#define rep(i,a,b) for(int i=(a); i<(b); ++i)
#define per(i,a,b) for(int i=(a)-1; i>=(b); --i)
#define ub upper_bound
#define lb lower_bound
#define pii pair<int,int>
#define pll pair<ll,ll>
#define vi vector<int>
#define vll vector<ll>

// ============================================================================
//                            ANSI COLOR CODES
// ============================================================================
const string RESET = "\033[0m";
const string BOLD  = "\033[1m";
const string RED   = "\033[31m";
const string GREEN = "\033[32m";
const string YELLOW= "\033[33m";
const string BLUE  = "\033[34m";
const string CYAN  = "\033[36m";
const string MAGENTA="\033[35m";

// ============================================================================
//                              DATA STRUCTURES
// ============================================================================
struct Activity {
    int id, name_id, start, finish, weight, deadline;
};

// ============================================================================
//                       DISJOINT SET UNION (Fast & Simple)
// ============================================================================
class DSU {
public:
    vi parent;
    DSU(int n) : parent(n + 1) {
        iota(all(parent), 0);
    }
    int find(int x) {
        return parent[x] == x ? x : parent[x] = find(parent[x]);
    }
    void unite(int u, int v) {
        parent[find(u)] = find(v);
    }
};

// ============================================================================
//                         TIME CONVERSION (No Validation)
// ============================================================================
int timeToMinutes(string t) {
    int h, m;
    sscanf(t.c_str(), "%d:%d", &h, &m);
    return h * 60 + m;
}

string minutesToTime(int mins) {
    int h = mins / 60, m = mins % 60;
    char buf[16];
    sprintf(buf, "%02d:%02d", h, m);
    return string(buf);
}

// ============================================================================
//                              UTILITY FUNCTION
// ============================================================================
void printDivider(char c = '=', int n = 75) {
    cout << CYAN << string(n, c) << RESET << "\n";
}

void printHeader(const string& title) {
    printDivider();
    cout << BOLD << CYAN << "  " << title << RESET << "\n";
    printDivider();
}

// ============================================================================
//   ALGORITHM 1: ACTIVITY SELECTION (Greedy - Earliest Finish Time)
//   Time: O(N log N), Space: O(N)
// ============================================================================
vector<Activity> activitySelection(vector<Activity> acts) {
    sort(all(acts), [](const Activity& a, const Activity& b) {
        return a.finish < b.finish;
    });
    
    vector<Activity> selected;
    int lastFinish = -1;
    
    rep(i, 0, sz(acts)) {
        if (acts[i].start >= lastFinish) {
            selected.pb(acts[i]);
            lastFinish = acts[i].finish;
        }
    }
    return selected;
}

// ============================================================================
//   ALGORITHM 2: WEIGHTED INTERVAL SCHEDULING (Greedy - Weight/Duration)
//   Time: O(N²), Space: O(N)
// ============================================================================
vector<Activity> weightedScheduling(vector<Activity> acts) {
    sort(all(acts), [](const Activity& a, const Activity& b) {
        if (a.weight != b.weight) return a.weight > b.weight;
        return a.finish < b.finish;
    });
    
    vector<Activity> selected;
    rep(i, 0, sz(acts)) {
        bool conflict = false;
        rep(j, 0, sz(selected)) {
            if (max(acts[i].start, selected[j].start) < min(acts[i].finish, selected[j].finish)) {
                conflict = true;
                break;
            }
        }
        if (!conflict) selected.pb(acts[i]);
    }
    
    sort(all(selected), [](const Activity& a, const Activity& b) {
        return a.start < b.start;
    });
    return selected;
}

// ============================================================================
//   ALGORITHM 3: JOB SEQUENCING WITH DEADLINES (DSU Optimized)
//   Time: O(N log N + N·α(N)), Space: O(N)
// ============================================================================
vector<Activity> jobSequencingDSU(vector<Activity> jobs) {
    if (sz(jobs) == 0) return {};
    
    sort(all(jobs), [](const Activity& a, const Activity& b) {
        return a.weight > b.weight;
    });
    
    int maxDl = 0;
    rep(i, 0, sz(jobs)) maxDl = max(maxDl, jobs[i].deadline);
    
    DSU dsu(maxDl);
    vector<Activity> result(maxDl + 1);
    vector<bool> filled(maxDl + 1, false);
    
    rep(i, 0, sz(jobs)) {
        int slot = dsu.find(jobs[i].deadline);
        if (slot > 0) {
            result[slot] = jobs[i];
            filled[slot] = true;
            dsu.unite(slot, slot - 1);
        }
    }
    
    vector<Activity> scheduled;
    rep(i, 1, maxDl + 1) {
        if (filled[i]) scheduled.pb(result[i]);
    }
    return scheduled;
}

// ============================================================================
//   ALGORITHM 4: MINIMUM ROOMS REQUIRED (Priority Queue)
//   Time: O(N log N), Space: O(N)
// ============================================================================
int minRoomsRequired(vector<Activity> acts, vector<vector<Activity>>& rooms) {
    sort(all(acts), [](const Activity& a, const Activity& b) {
        return a.start < b.start;
    });
    
    priority_queue<pii, vector<pii>, greater<pii>> pq;
    int roomCount = 0;
    rooms.clear();
    
    rep(i, 0, sz(acts)) {
        if (!pq.empty() && pq.top().first <= acts[i].start) {
            int rid = pq.top().second;
            pq.pop();
            rooms[rid].pb(acts[i]);
            pq.push({acts[i].finish, rid});
        } else {
            rooms.pb({{acts[i]}});
            pq.push({acts[i].finish, roomCount});
            roomCount++;
        }
    }
    return roomCount;
}

// ============================================================================
//                              DISPLAY FUNCTIONS
// ============================================================================
map<int, string> activityNames;

void displayActivities(const vector<Activity>& acts, const string& title) {
    cout << "\n" << BOLD << YELLOW << title << RESET << "\n";
    if (sz(acts) == 0) {
        cout << RED << "  (no activities)\n" << RESET;
        return;
    }
    cout << BOLD << left << setw(5) << "ID" << setw(20) << "Activity" << setw(10) << "Start"
         << setw(10) << "Finish" << setw(10) << "Duration" << setw(10) << "Priority" << RESET << "\n";
    cout << string(65, '-') << "\n";
    
    rep(i, 0, sz(acts)) {
        cout << left << setw(5) << acts[i].id
             << setw(20) << activityNames[acts[i].name_id]
             << setw(10) << minutesToTime(acts[i].start)
             << setw(10) << minutesToTime(acts[i].finish)
             << setw(10) << (to_string(acts[i].finish - acts[i].start) + " min")
             << setw(10) << acts[i].weight << "\n";
    }
}

void displayRoomAssignment(const vector<vector<Activity>>& rooms) {
    cout << "\n" << BOLD << GREEN << "Room-wise Allocation:" << RESET << "\n";
    rep(i, 0, sz(rooms)) {
        cout << BOLD << MAGENTA << "  Room " << (i + 1) << ":" << RESET;
        rep(j, 0, sz(rooms[i])) {
            cout << " [" << activityNames[rooms[i][j].name_id] << " "
                 << minutesToTime(rooms[i][j].start) << "-"
                 << minutesToTime(rooms[i][j].finish) << "]";
        }
        cout << "\n";
    }
}

void displayTimetableGrid(const vector<Activity>& acts) {
    if (sz(acts) == 0) return;
    cout << "\n" << BOLD << BLUE << "Visual Timetable (1 char = 30 min):" << RESET << "\n";
    
    int minStart = INT_MAX, maxFinish = 0;
    rep(i, 0, sz(acts)) {
        minStart = min(minStart, acts[i].start);
        maxFinish = max(maxFinish, acts[i].finish);
    }
    minStart = (minStart / 30) * 30;
    int cells = (maxFinish - minStart + 29) / 30;
    
    cout << "       ";
    rep(i, 0, cells) if (i % 2 == 0) cout << left << setw(2) << minutesToTime(minStart + i * 30);
    cout << "\n";
    
    rep(i, 0, sz(acts)) {
        cout << CYAN << left << setw(7) << activityNames[acts[i].name_id].substr(0, 6) << RESET;
        int startCell = (acts[i].start - minStart) / 30;
        int endCell = (acts[i].finish - minStart + 29) / 30;
        rep(j, 0, cells) {
            if (j >= startCell && j < endCell) cout << GREEN << "█" << RESET;
            else cout << "·";
        }
        cout << "\n";
    }
}

// ============================================================================
//                              SAMPLE DATA & INPUT
// ============================================================================
vector<Activity> getSampleData() {
    vector<Activity> acts;
    
    activityNames[1] = "Math";
    acts.pb({1, 1, 540, 600, 5, 720});
    
    activityNames[2] = "Physics";
    acts.pb({2, 2, 600, 690, 4, 720});
    
    activityNames[3] = "Chemistry";
    acts.pb({3, 3, 570, 660, 3, 690});
    
    activityNames[4] = "CS-Lab";
    acts.pb({4, 4, 660, 780, 5, 840});
    
    activityNames[5] = "English";
    acts.pb({5, 5, 690, 750, 2, 810});
    
    activityNames[6] = "DSA";
    acts.pb({6, 6, 780, 870, 5, 900});
    
    activityNames[7] = "Sports";
    acts.pb({7, 7, 840, 900, 1, 960});
    
    activityNames[8] = "Library";
    acts.pb({8, 8, 900, 990, 3, 1020});
    
    activityNames[9] = "Workshop";
    acts.pb({9, 9, 960, 1080, 4, 1080});
    
    activityNames[10] = "Seminar";
    acts.pb({10, 10, 870, 960, 4, 990});
    
    return acts;
}

vector<Activity> getUserInput() {
    int n;
    cout << CYAN << "\nEnter number of activities: " << RESET;
    cin >> n;
    
    vector<Activity> acts;
    string startStr, finishStr, dlStr;
    
    rep(i, 0, n) {
        cout << YELLOW << "\n--- Activity " << (i + 1) << " ---\n" << RESET;
        
        string name;
        cout << "  Name: ";
        cin >> name;
        
        activityNames[i + 1] = name;
        
        cout << "  Start time (HH:MM): ";
        cin >> startStr;
        
        cout << "  Finish time (HH:MM): ";
        cin >> finishStr;
        
        int weight;
        cout << "  Priority/Weight (1-10): ";
        cin >> weight;
        
        cout << "  Deadline (HH:MM): ";
        cin >> dlStr;
        
        int start = timeToMinutes(startStr);
        int finish = timeToMinutes(finishStr);
        int deadline = timeToMinutes(dlStr) / 60;
        
        acts.pb({i + 1, i + 1, start, finish, weight, deadline});
    }
    return acts;
}

// ============================================================================
//                              MAIN ANALYSIS
// ============================================================================
void runFullAnalysis(vector<Activity> acts) {
    printHeader("INPUT ACTIVITIES");
    displayActivities(acts, "All Activities (Original)");
    
    printHeader("1. ACTIVITY SELECTION (Maximize count - Earliest Finish Time)");
    auto sel1 = activitySelection(acts);
    displayActivities(sel1, "Selected Activities (Greedy by Finish Time)");
    cout << GREEN << "\n  Total selected: " << sz(sel1) << "/" << sz(acts) << RESET << "\n";
    displayTimetableGrid(sel1);
    
    printHeader("2. PRIORITY-BASED WEIGHTED SCHEDULING");
    auto sel2 = weightedScheduling(acts);
    int totalWeight = 0;
    rep(i, 0, sz(sel2)) totalWeight += sel2[i].weight;
    displayActivities(sel2, "Selected Activities (Greedy by Priority)");
    cout << GREEN << "\n  Total priority score: " << totalWeight << RESET << "\n";
    
    printHeader("3. JOB SEQUENCING WITH DEADLINES (DSU Optimized)");
    auto sel3 = jobSequencingDSU(acts);
    int totalProfit = 0;
    rep(i, 0, sz(sel3)) totalProfit += sel3[i].weight;
    displayActivities(sel3, "Scheduled Jobs (Maximize Profit before Deadlines)");
    cout << GREEN << "\n  Total profit: " << totalProfit << RESET << "\n";
    
    printHeader("4. MINIMUM ROOMS REQUIRED (Meeting Rooms II)");
    vector<vector<Activity>> rooms;
    int roomCount = minRoomsRequired(acts, rooms);
    cout << BOLD << GREEN << "  Minimum rooms required to fit ALL activities: "
         << roomCount << RESET << "\n";
    displayRoomAssignment(rooms);
    
    printHeader("COMPARATIVE SUMMARY");
    cout << BOLD << left << setw(40) << "Algorithm" << setw(15) << "Selected"
         << setw(15) << "Score" << RESET << "\n";
    cout << string(70, '-') << "\n";
    cout << left << setw(40) << "Activity Selection (Max Count)"
         << setw(15) << sz(sel1) << setw(15) << "-" << "\n";
    cout << left << setw(40) << "Priority-based Greedy"
         << setw(15) << sz(sel2) << setw(15) << totalWeight << "\n";
    cout << left << setw(40) << "Job Sequencing (DSU)"
         << setw(15) << sz(sel3) << setw(15) << totalProfit << "\n";
    cout << left << setw(40) << "Min Rooms (all scheduled)"
         << setw(15) << sz(acts) << setw(15) << roomCount << " rooms\n";
}

// ============================================================================
//                                  MAIN
// ============================================================================
int main() {
    fastio;
    cout << BOLD << CYAN << R"(
╔═══════════════════════════════════════════════════════════════════════════╗
║          GREEDY-BASED SCHEDULING / TIMETABLE SYSTEM (C++17)               ║
║          Algorithms: Activity Selection | Job Sequencing | Min-Heap        ║
║                      DSU-Optimized | Sweep Line | Priority Queue           ║
╚═══════════════════════════════════════════════════════════════════════════╝
)" << RESET;
    
    while (true) {
        cout << "\n" << BOLD << YELLOW
             << "MENU:\n"
             << "  1. Run with sample university timetable\n"
             << "  2. Enter custom activities\n"
             << "  3. Exit\n"
             << RESET
             << "Choice: ";
        int choice;
        cin >> choice;
        
        if (choice == 1) {
            runFullAnalysis(getSampleData());
        } else if (choice == 2) {
            runFullAnalysis(getUserInput());
        } else {
            cout << GREEN << "Exiting. Goodbye!\n" << RESET;
            break;
        }
    }
    return 0;
}
