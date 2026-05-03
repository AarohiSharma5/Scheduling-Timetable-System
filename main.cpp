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
#include <set>
#include <fstream>
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

struct AnalyticsResult {
    int totalActivities;
    int selectedActivities;
    int totalWeight;
    double utilizationPercent;
    int idleTimeMinutes;
    int timeSlotCoverage;
};

struct ConflictReport {
    vector<pii> conflictPairs;  // (activity_id, activity_id)
    int totalConflicts;
    bool hasConflicts;
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

map<int, string> activityNames;

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
//   ALGORITHM 5: WEIGHTED INTERVAL SCHEDULING (DP - OPTIMAL SOLUTION)
//   Time: O(N² or N log N), Space: O(N)
//   THIS SOLVES THE PROBLEM OPTIMALLY (unlike greedy approximation)
// ============================================================================
vector<Activity> weightedIntervalSchedulingDP(vector<Activity> acts) {
    if (sz(acts) == 0) return {};
    
    // Sort by finish time
    sort(all(acts), [](const Activity& a, const Activity& b) {
        return a.finish < b.finish;
    });
    
    int n = sz(acts);
    vi dp(n);  // dp[i] = max weight considering activities 0..i
    vi parent_idx(n, -1);
    
    // Find latest activity that doesn't conflict
    auto findLatest = [&](int idx) {
        int lo = 0, hi = idx - 1;
        int res = -1;
        while (lo <= hi) {
            int mid = (lo + hi) / 2;
            if (acts[mid].finish <= acts[idx].start) {
                res = mid;
                lo = mid + 1;
            } else {
                hi = mid - 1;
            }
        }
        return res;
    };
    
    // DP: for each activity, either include or exclude
    dp[0] = acts[0].weight;
    rep(i, 1, n) {
        int inclWeight = acts[i].weight;
        int latest = findLatest(i);
        if (latest != -1) inclWeight += dp[latest];
        
        if (inclWeight > dp[i-1]) {
            dp[i] = inclWeight;
            parent_idx[i] = latest;
        } else {
            dp[i] = dp[i-1];
            parent_idx[i] = -2;  // exclude marker
        }
    }
    
    // Backtrack to find selected activities
    vector<Activity> selected;
    int idx = n - 1;
    while (idx >= 0) {
        if (parent_idx[idx] != -2) {
            selected.pb(acts[idx]);
            idx = parent_idx[idx];
        } else {
            idx--;
        }
    }
    
    reverse(all(selected));
    return selected;
}

// ============================================================================
//   CONFLICT DETECTION & REPORTING
// ============================================================================
ConflictReport detectConflicts(const vector<Activity>& acts) {
    ConflictReport report;
    report.totalConflicts = 0;
    report.hasConflicts = false;
    
    rep(i, 0, sz(acts)) {
        rep(j, i+1, sz(acts)) {
            if (max(acts[i].start, acts[j].start) < min(acts[i].finish, acts[j].finish)) {
                report.conflictPairs.pb({acts[i].id, acts[j].id});
                report.totalConflicts++;
                report.hasConflicts = true;
            }
        }
    }
    return report;
}

// ============================================================================
//   ANALYTICS & STATISTICS
// ============================================================================
AnalyticsResult computeAnalytics(const vector<Activity>& allActs, const vector<Activity>& selected) {
    AnalyticsResult res;
    res.totalActivities = sz(allActs);
    res.selectedActivities = sz(selected);
    res.totalWeight = 0;
    
    int minTime = INT_MAX, maxTime = 0;
    rep(i, 0, sz(selected)) {
        res.totalWeight += selected[i].weight;
        minTime = min(minTime, selected[i].start);
        maxTime = max(maxTime, selected[i].finish);
    }
    
    if (minTime == INT_MAX) minTime = 0;
    
    int totalTimeSpan = maxTime - minTime;
    int usedTime = 0;
    
    rep(i, 0, sz(selected)) {
        usedTime += (selected[i].finish - selected[i].start);
    }
    
    res.timeSlotCoverage = totalTimeSpan > 0 ? totalTimeSpan : 0;
    res.utilizationPercent = totalTimeSpan > 0 ? (100.0 * usedTime / totalTimeSpan) : 0;
    res.idleTimeMinutes = totalTimeSpan - usedTime;
    
    return res;
}

// ============================================================================
//                              DISPLAY FUNCTIONS
// ============================================================================
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

void displayAnalytics(const AnalyticsResult& res) {
    cout << "\n" << BOLD << GREEN << "ANALYTICS:" << RESET << "\n";
    cout << "  Total Activities:      " << res.totalActivities << "\n";
    cout << "  Selected Activities:   " << res.selectedActivities << "\n";
    cout << "  Total Weight/Priority: " << res.totalWeight << "\n";
    cout << "  Time Slot Coverage:    " << res.timeSlotCoverage << " minutes\n";
    cout << "  Utilization Rate:      " << fixed << setprecision(1) << res.utilizationPercent << "%\n";
    cout << "  Idle Time:             " << res.idleTimeMinutes << " minutes\n";
}

void displayConflicts(const ConflictReport& report) {
    cout << "\n" << BOLD << CYAN << "CONFLICT ANALYSIS:" << RESET << "\n";
    if (!report.hasConflicts) {
        cout << GREEN << "  ✓ No conflicts detected!\n" << RESET;
        return;
    }
    cout << RED << "  ✗ " << report.totalConflicts << " conflict(s) found:\n" << RESET;
    rep(i, 0, sz(report.conflictPairs)) {
        cout << "    " << activityNames[report.conflictPairs[i].first] << " <-> "
             << activityNames[report.conflictPairs[i].second] << "\n";
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

void exportToCSV(const vector<Activity>& acts, const string& filename) {
    ofstream file(filename);
    file << "ID,Activity,Start,Finish,Duration(min),Priority\n";
    rep(i, 0, sz(acts)) {
        file << acts[i].id << "," << activityNames[acts[i].name_id] << ","
             << minutesToTime(acts[i].start) << "," << minutesToTime(acts[i].finish) << ","
             << (acts[i].finish - acts[i].start) << "," << acts[i].weight << "\n";
    }
    file.close();
    cout << GREEN << "✓ Exported to " << filename << RESET << "\n";
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
//                       COMPREHENSIVE ANALYSIS
// ============================================================================
void runFullAnalysis(vector<Activity> acts) {
    printHeader("INPUT ACTIVITIES");
    displayActivities(acts, "All Activities");
    
    auto conflicts = detectConflicts(acts);
    displayConflicts(conflicts);
    
    // ALGORITHM 1
    printHeader("1. ACTIVITY SELECTION (Greedy)");
    auto sel1 = activitySelection(acts);
    displayActivities(sel1, "Selected Activities (Greedy by Finish Time)");
    auto analytics1 = computeAnalytics(acts, sel1);
    displayAnalytics(analytics1);
    displayTimetableGrid(sel1);
    
    // ALGORITHM 2
    printHeader("2. PRIORITY-BASED WEIGHTED SCHEDULING (Greedy)");
    auto sel2 = weightedScheduling(acts);
    displayActivities(sel2, "Selected Activities (Greedy by Priority)");
    auto analytics2 = computeAnalytics(acts, sel2);
    displayAnalytics(analytics2);
    
    // ALGORITHM 3
    printHeader("3. JOB SEQUENCING WITH DEADLINES (DSU)");
    auto sel3 = jobSequencingDSU(acts);
    displayActivities(sel3, "Scheduled Jobs (Profit Maximization)");
    auto analytics3 = computeAnalytics(acts, sel3);
    displayAnalytics(analytics3);
    
    // ALGORITHM 4
    printHeader("4. MINIMUM ROOMS REQUIRED (Min Heap)");
    vector<vector<Activity>> rooms;
    int roomCount = minRoomsRequired(acts, rooms);
    cout << BOLD << GREEN << "  Minimum rooms: " << roomCount << RESET << "\n";
    displayRoomAssignment(rooms);
    
    // ALGORITHM 5 - NEW: DP OPTIMAL
    printHeader("5. WEIGHTED INTERVAL SCHEDULING (DP - OPTIMAL)");
    auto sel5 = weightedIntervalSchedulingDP(acts);
    displayActivities(sel5, "OPTIMAL Solution (DP Algorithm)");
    auto analytics5 = computeAnalytics(acts, sel5);
    displayAnalytics(analytics5);
    
    // COMPARISON
    printHeader("COMPREHENSIVE COMPARISON");
    cout << BOLD << left << setw(40) << "Algorithm" << setw(12) << "Selected"
         << setw(12) << "Weight" << setw(12) << "Util%" << RESET << "\n";
    cout << string(76, '-') << "\n";
    cout << left << setw(40) << "1. Activity Selection (Greedy)"
         << setw(12) << analytics1.selectedActivities
         << setw(12) << analytics1.totalWeight
         << fixed << setprecision(1) << setw(12) << analytics1.utilizationPercent << "%\n";
    cout << left << setw(40) << "2. Weighted Scheduling (Greedy)"
         << setw(12) << analytics2.selectedActivities
         << setw(12) << analytics2.totalWeight
         << fixed << setprecision(1) << setw(12) << analytics2.utilizationPercent << "%\n";
    cout << left << setw(40) << "3. Job Sequencing (DSU)"
         << setw(12) << analytics3.selectedActivities
         << setw(12) << analytics3.totalWeight
         << fixed << setprecision(1) << setw(12) << analytics3.utilizationPercent << "%\n";
    cout << left << setw(40) << "4. Min Rooms (Heap)" << setw(12) << acts.size()
         << setw(12) << "-" << setw(12) << "100%" << "\n";
    cout << left << setw(40) << "5. Weighted Interval (DP-OPTIMAL) ★"
         << setw(12) << analytics5.selectedActivities
         << setw(12) << analytics5.totalWeight << fixed << setprecision(1)
         << setw(12) << analytics5.utilizationPercent << "%\n";
    
    // Export option
    cout << "\n" << BOLD << YELLOW << "Export to CSV? (1=Yes, 0=No): " << RESET;
    int exportChoice;
    cin >> exportChoice;
    if (exportChoice == 1) {
        exportToCSV(sel5, "schedule_output.csv");
    }
}

// ============================================================================
//                           ADVANCED MENU
// ============================================================================
void advancedMenu(vector<Activity>& acts) {
    while (true) {
        cout << "\n" << BOLD << CYAN << "ADVANCED OPTIONS:\n" << RESET
             << "  1. View all algorithms side-by-side\n"
             << "  2. Detect and report conflicts\n"
             << "  3. View analytics for any algorithm\n"
             << "  4. Export schedule to CSV\n"
             << "  5. Compare resource utilization\n"
             << "  6. Back to main menu\n" << RESET << "Choice: ";
        int choice;
        cin >> choice;
        
        if (choice == 6) break;
        
        if (choice == 1) {
            runFullAnalysis(acts);
        } else if (choice == 2) {
            auto report = detectConflicts(acts);
            displayConflicts(report);
        } else if (choice == 3) {
            cout << "\nChoose algorithm: 1-5: ";
            int algo;
            cin >> algo;
            vector<Activity> result;
            if (algo == 1) result = activitySelection(acts);
            else if (algo == 2) result = weightedScheduling(acts);
            else if (algo == 3) result = jobSequencingDSU(acts);
            else if (algo == 5) result = weightedIntervalSchedulingDP(acts);
            
            if (sz(result) > 0) {
                auto res = computeAnalytics(acts, result);
                displayAnalytics(res);
            }
        } else if (choice == 4) {
            cout << "Filename (default: schedule.csv): ";
            string fname;
            cin.ignore();
            getline(cin, fname);
            if (fname.empty()) fname = "schedule.csv";
            exportToCSV(weightedIntervalSchedulingDP(acts), fname);
        } else if (choice == 5) {
            auto sel1 = activitySelection(acts);
            auto sel2 = weightedScheduling(acts);
            auto sel5 = weightedIntervalSchedulingDP(acts);
            
            auto a1 = computeAnalytics(acts, sel1);
            auto a2 = computeAnalytics(acts, sel2);
            auto a5 = computeAnalytics(acts, sel5);
            
            cout << "\n" << BOLD << MAGENTA << "UTILIZATION COMPARISON:" << RESET << "\n";
            cout << "Algorithm 1: " << fixed << setprecision(1) << a1.utilizationPercent << "%\n";
            cout << "Algorithm 2: " << fixed << setprecision(1) << a2.utilizationPercent << "%\n";
            cout << "Algorithm 5 (Optimal): " << fixed << setprecision(1) << a5.utilizationPercent << "%\n";
        }
    }
}

// ============================================================================
//                                  MAIN
// ============================================================================
int main() {
    fastio;
    cout << BOLD << CYAN << R"(
╔═══════════════════════════════════════════════════════════════════════════╗
║         ADVANCED GREEDY SCHEDULING SYSTEM (5 ALGORITHMS + ANALYTICS)      ║
║     Activity Selection | Weighted Scheduling | Job Sequencing | DP Opt    ║
║              DSU-Optimized | Priority Queue | Dynamic Programming         ║
╚═══════════════════════════════════════════════════════════════════════════╝
)" << RESET;
    
    while (true) {
        cout << "\n" << BOLD << YELLOW
             << "MAIN MENU:\n"
             << "  1. Run with sample university timetable\n"
             << "  2. Enter custom activities\n"
             << "  3. Advanced options & analytics\n"
             << "  4. Exit\n"
             << RESET << "Choice: ";
        int choice;
        cin >> choice;
        
        if (choice == 1) {
            auto acts = getSampleData();
            runFullAnalysis(acts);
        } else if (choice == 2) {
            auto acts = getUserInput();
            if (sz(acts) > 0) runFullAnalysis(acts);
        } else if (choice == 3) {
            auto acts = getSampleData();
            advancedMenu(acts);
        } else if (choice == 4) {
            cout << GREEN << "Exiting. Goodbye!\n" << RESET;
            break;
        }
    }
    return 0;
}
