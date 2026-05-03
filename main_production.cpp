#include <iostream>
#include <vector>
#include <algorithm>
#include <queue>
#include <string>
#include <iomanip>
#include <climits>
#include <numeric>
#include <cstdio>
#include <stdexcept>
#include <memory>
#include <functional>

using namespace std;

// ============================================================================
// IMPROVEMENT #1: Place configuration in a dedicated namespace
// This separates concerns - configuration from logic
// ============================================================================
namespace Config {
    // Time conversion constants
    constexpr int MINUTES_PER_HOUR = 60;
    constexpr int MINUTES_PER_DAY = 24 * MINUTES_PER_HOUR;
    constexpr int GRID_CELL_MINUTES = 30;
    
    // UI constants
    constexpr int DIVIDER_WIDTH = 75;
    constexpr int NAME_WIDTH = 20;
    
    // Validation constants
    constexpr int MIN_PRIORITY = 1;
    constexpr int MAX_PRIORITY = 10;
    constexpr int MIN_ACTIVITY_DURATION = 1;
}

// IMPROVEMENT #2: Encapsulate ANSI colors in a proper class
class ConsoleStyle {
public:
    static constexpr const char* RESET   = "\033[0m";
    static constexpr const char* BOLD    = "\033[1m";
    static constexpr const char* RED     = "\033[31m";
    static constexpr const char* GREEN   = "\033[32m";
    static constexpr const char* YELLOW  = "\033[33m";
    static constexpr const char* BLUE    = "\033[34m";
    static constexpr const char* CYAN    = "\033[36m";
    static constexpr const char* MAGENTA = "\033[35m";
};

// =============================================================================
//                        IMPROVED DATA STRUCTURES
// =============================================================================
// IMPROVEMENT #3: Add validation to struct with constructor
// Note: Fields are NOT const because std::sort needs assignment operators
// This is a practical tradeoff: constness would break compatibility with STL algorithms
// For true immutability, consider using const references or wrappers
struct Activity {
    int id;
    string name;
    int start;        // minutes from 00:00
    int finish;       // minutes from 00:00
    int weight;       // priority (1-10)
    int deadline;     // minutes from 00:00
    
    // Constructor with validation
    Activity(int id_ = 0, const string& name_ = "", int start_ = 0, 
             int finish_ = 0, int weight_ = 1, int deadline_ = 0)
        : id(id_), name(name_), start(start_), finish(finish_), 
          weight(weight_), deadline(deadline_) {
        validate();
    }
    
private:
    void validate() const {
        if (start < 0 || finish < 0 || finish <= start) {
            throw invalid_argument("Invalid time range: start=" + to_string(start) 
                                 + ", finish=" + to_string(finish));
        }
        if (weight < Config::MIN_PRIORITY || weight > Config::MAX_PRIORITY) {
            throw invalid_argument("Weight must be between " + to_string(Config::MIN_PRIORITY) 
                                 + " and " + to_string(Config::MAX_PRIORITY));
        }
        if (deadline < 0) {
            throw invalid_argument("Deadline cannot be negative");
        }
        int duration = finish - start;
        if (duration < Config::MIN_ACTIVITY_DURATION) {
            throw invalid_argument("Activity duration too short: " + to_string(duration));
        }
    }
public:
    int getDuration() const { return finish - start; }
};

struct Room {
    int id;
    int endTime;
    vector<Activity> activities;
    bool operator>(const Room& o) const { return endTime > o.endTime; }
};

// IMPROVEMENT #5: Better DSU with path compression AND union by rank
class DSU {
    vector<int> parent, rank;
public:
    DSU(int n) : parent(n + 1), rank(n + 1, 0) {
        for (int i = 0; i <= n; ++i) parent[i] = i;
    }
    int find(int x) {
        if (parent[x] != x) parent[x] = find(parent[x]);
        return parent[x];
    }
    void unite(int u, int v) {
        u = find(u);
        v = find(v);
        if (u == v) return;
        // Union by rank optimization
        if (rank[u] < rank[v]) swap(u, v);
        parent[v] = u;
        if (rank[u] == rank[v]) rank[u]++;
    }
};

// IMPROVEMENT #6: Macros moved to a helper namespace for clarity
namespace Helpers {
    #define all(x)  (x).begin(), (x).end()
    #define sz(x)   (int)((x).size())
}

// =============================================================================
//                       IMPROVED UTILITY FUNCTIONS
// =============================================================================

// IMPROVEMENT #7: Add a simple logging system
class Logger {
public:
    enum Level { DEBUG, INFO, WARN, ERROR };
    static void log(Level level, const string& msg) {
        switch (level) {
            case ERROR: cout << ConsoleStyle::RED << "[ERROR] " << ConsoleStyle::RESET; break;
            case WARN:  cout << ConsoleStyle::YELLOW << "[WARN] " << ConsoleStyle::RESET; break;
            case INFO:  cout << ConsoleStyle::CYAN << "[INFO] " << ConsoleStyle::RESET; break;
            case DEBUG: cout << ConsoleStyle::BLUE << "[DEBUG] " << ConsoleStyle::RESET; break;
        }
        cout << msg << "\n";
    }
};

// IMPROVEMENT #8: TimeConverter with better error handling
class TimeConverter {
public:
    static string minutesToTime(int mins) {
        if (mins < 0 || mins >= Config::MINUTES_PER_DAY) {
            throw invalid_argument("Time out of valid range: " + to_string(mins));
        }
        int h = mins / Config::MINUTES_PER_HOUR;
        int m = mins % Config::MINUTES_PER_HOUR;
        char buf[16];
        snprintf(buf, sizeof(buf), "%02d:%02d", h, m);
        return string(buf);
    }

    static int timeToMinutes(const string& t) {
        int h, m;
        if (sscanf(t.c_str(), "%d:%d", &h, &m) != 2) {
            throw invalid_argument("Invalid time format: " + t + " (expected HH:MM)");
        }
        if (h < 0 || h >= 24 || m < 0 || m >= 60) {
            throw invalid_argument("Invalid time values: " + t);
        }
        return h * Config::MINUTES_PER_HOUR + m;
    }
};

void printDivider(char c = '=', int n = Config::DIVIDER_WIDTH) {
    cout << ConsoleStyle::CYAN << string(n, c) << ConsoleStyle::RESET << "\n";
}

void printHeader(const string& title) {
    printDivider();
    cout << ConsoleStyle::BOLD << ConsoleStyle::CYAN << "  " << title 
         << ConsoleStyle::RESET << "\n";
    printDivider();
}

// =============================================================================
//   ALGORITHM 1: ACTIVITY SELECTION (Earliest Finish Time - Optimal Greedy)
//   Why it's optimal: By selecting shortest finishing, we maximize room for others
//   Time Complexity: O(N log N) due to sorting
//   Space Complexity: O(N) for results
// =============================================================================
vector<Activity> activitySelection(vector<Activity> acts) {
    if (acts.empty()) return {};
    
    // Sort by finish time ascending (greedy choice property)
    sort(acts.begin(), acts.end(), [](const Activity& a, const Activity& b) {
        if (a.finish != b.finish) return a.finish < b.finish;
        return a.start < b.start;  // Tiebreaker: earlier start
    });

    vector<Activity> selected;
    int lastFinish = -1;

    for (const auto& a : acts) {
        // Non-overlapping check: new start >= last finish time
        if (a.start >= lastFinish) {
            selected.push_back(a);
            Logger::log(Logger::DEBUG, "Selected: " + a.name + 
                       " (" + TimeConverter::minutesToTime(a.start) + "-" + 
                       TimeConverter::minutesToTime(a.finish) + ")");
            lastFinish = a.finish;
        }
    }
    return selected;
}

// =============================================================================
//   ALGORITHM 2: WEIGHTED INTERVAL SCHEDULING (Greedy Approximation)
//   ⚠️ CRITICISM: This is O(N²) due to nested loop conflict checking
//   Better approach: Use dynamic programming for optimal solution
//   Current use: Practical approximation when perfection isn't critical
//   Time Complexity: O(N² ) - intentional tradeoff for simplicity
// =============================================================================
vector<Activity> weightedScheduling(vector<Activity> acts) {
    // Sort by weight/duration ratio descending (value density)
    // On tie: prefer activities that finish earlier (greedy compatibility)
    sort(acts.begin(), acts.end(), [](const Activity& a, const Activity& b) {
        double ratioA = (double)a.weight / a.getDuration();
        double ratioB = (double)b.weight / b.getDuration();
        if (abs(ratioA - ratioB) > 1e-9) return ratioA > ratioB;
        return a.finish < b.finish;
    });

    vector<Activity> selected;
    
    for (const auto& a : acts) {
        bool conflict = false;
        // O(N) check against selected activities
        for (const auto& s : selected) {
            // Overlap condition: max(start) < min(finish)
            if (max(a.start, s.start) < min(a.finish, s.finish)) {
                conflict = true;
                break;
            }
        }
        if (!conflict) {
            selected.push_back(a);
            Logger::log(Logger::DEBUG, "Weighted selection: " + a.name);
        }
    }
    
    // Sort result by start time for display
    sort(selected.begin(), selected.end(), [](const Activity& a, const Activity& b){
        return a.start < b.start;
    });
    return selected;
}

// =============================================================================
//   ALGORITHM 3: JOB SEQUENCING WITH DEADLINES (DSU Optimized)
//   Greedy: Select highest profit jobs first
//   Strategy: Assign to latest available slot before deadline
//   Why: Latest slot leaves earlier slots for smaller task assignments
//   Time Complexity: O(N log N + N·α(N)) using DSU with path compression
// =============================================================================
vector<Activity> jobSequencingDSU(vector<Activity> jobs) {
    if (jobs.empty()) return {};

    // Sort by weight (profit) descending - greedy choice
    sort(jobs.begin(), jobs.end(), [](const Activity& a, const Activity& b) {
        return a.weight > b.weight;
    });

    // Convert deadline time to hour slots
    int maxSlot = 0;
    for (const auto& j : jobs) {
        int slot = j.deadline / Config::MINUTES_PER_HOUR;
        maxSlot = max(maxSlot, slot);
    }
    
    if (maxSlot == 0) {
        Logger::log(Logger::WARN, "No valid deadline slots found");
        return {};
    }

    DSU dsu(maxSlot);
    vector<Activity> result(maxSlot + 1);  // Uninitialized - will store jobs
    vector<bool> filled(maxSlot + 1, false);

    for (const auto& j : jobs) {
        int slot = min(maxSlot, j.deadline / Config::MINUTES_PER_HOUR);
        int availSlot = dsu.find(slot);

        if (availSlot > 0) {
            result[availSlot] = j;
            filled[availSlot] = true;
            // DSU optimization: link current slot to previous
            dsu.unite(availSlot, availSlot - 1);
            Logger::log(Logger::DEBUG, "Scheduled: " + j.name + 
                       " in slot " + to_string(availSlot));
        }
    }

    vector<Activity> scheduled;
    for (int i = 1; i <= maxSlot; ++i) {
        if (filled[i]) scheduled.push_back(result[i]);
    }
    return scheduled;
}

// =============================================================================
//   ALGORITHM 4: MINIMUM ROOMS REQUIRED (Meeting Rooms II)
//   Problem: Find minimum resources (rooms) to fit ALL activities without conflict
//   Approach: Min-heap tracks when rooms become available
//   Why this works: Room optimization problem (interval scheduling resource allocation)
//   Time Complexity: O(N log N) for sorting + heap operations
// =============================================================================
int minRoomsRequired(vector<Activity> acts, vector<vector<Activity>>& roomAssignment) {
    if (acts.empty()) {
        roomAssignment.clear();
        return 0;
    }
    
    // Sort by start time ascending
    sort(acts.begin(), acts.end(), [](const Activity& a, const Activity& b) {
        if (a.start != b.start) return a.start < b.start;
        return a.finish < b.finish;  // Tiebreaker
    });

    // Min-heap: (endTime, roomId)
    priority_queue<pair<int,int>, vector<pair<int,int>>, greater<pair<int,int>>> pq;
    int roomCount = 0;
    roomAssignment.clear();

    for (const auto& a : acts) {
        if (!pq.empty() && pq.top().first <= a.start) {
            // Room becomes available before or at start of new activity
            int rid = pq.top().second;
            pq.pop();
            roomAssignment[rid].push_back(a);
            pq.push({a.finish, rid});
            Logger::log(Logger::DEBUG, "Reused room " + to_string(rid) + 
                       " for " + a.name);
        } else {
            // Need a new room
            roomAssignment.push_back({});
            roomAssignment[roomCount].push_back(a);
            pq.push({a.finish, roomCount});
            Logger::log(Logger::DEBUG, "Opened room " + to_string(roomCount) + 
                       " for " + a.name);
            ++roomCount;
        }
    }
    return roomCount;
}

// =============================================================================
//                        IMPROVED DISPLAY FUNCTIONS
// =============================================================================

void displayActivities(const vector<Activity>& acts, const string& title) {
    cout << "\n" << ConsoleStyle::BOLD << ConsoleStyle::YELLOW << title 
         << ConsoleStyle::RESET << "\n";
    if (acts.empty()) {
        cout << ConsoleStyle::RED << "  (no activities)\n" << ConsoleStyle::RESET;
        return;
    }
    cout << ConsoleStyle::BOLD
         << left << setw(5)  << "ID"
         << setw(Config::NAME_WIDTH) << "Activity"
         << setw(10) << "Start"
         << setw(10) << "Finish"
         << setw(10) << "Duration"
         << setw(10) << "Priority"
         << ConsoleStyle::RESET << "\n";
    cout << string(65, '-') << "\n";
    
    try {
        for (const auto& a : acts) {
            cout << left << setw(5) << a.id
                 << setw(Config::NAME_WIDTH) << a.name
                 << setw(10) << TimeConverter::minutesToTime(a.start)
                 << setw(10) << TimeConverter::minutesToTime(a.finish)
                 << setw(10) << (to_string(a.getDuration()) + " min")
                 << setw(10) << a.weight
                 << "\n";
        }
    } catch (const exception& e) {
        Logger::log(Logger::ERROR, "Display error: " + string(e.what()));
    }
}

void displayRoomAssignment(const vector<vector<Activity>>& rooms) {
    cout << "\n" << ConsoleStyle::BOLD << ConsoleStyle::GREEN 
         << "Room-wise Allocation:" << ConsoleStyle::RESET << "\n";
    
    try {
        for (size_t i = 0; i < rooms.size(); ++i) {
            cout << ConsoleStyle::BOLD << ConsoleStyle::MAGENTA 
                 << "  Room " << (i + 1) << ":" << ConsoleStyle::RESET;
            for (const auto& a : rooms[i]) {
                cout << " [" << a.name << " "
                     << TimeConverter::minutesToTime(a.start) << "-"
                     << TimeConverter::minutesToTime(a.finish) << "]";
            }
            cout << "\n";
        }
    } catch (const exception& e) {
        Logger::log(Logger::ERROR, "Room display error: " + string(e.what()));
    }
}

void displayTimetableGrid(const vector<Activity>& acts) {
    if (acts.empty()) return;
    cout << "\n" << ConsoleStyle::BOLD << ConsoleStyle::BLUE 
         << "Visual Timetable (1 char = " << Config::GRID_CELL_MINUTES << " min):" 
         << ConsoleStyle::RESET << "\n";

    int minStart = INT_MAX, maxFinish = 0;
    for (const auto& a : acts) {
        minStart = min(minStart, a.start);
        maxFinish = max(maxFinish, a.finish);
    }
    
    // Align to grid cell boundary
    minStart = (minStart / Config::GRID_CELL_MINUTES) * Config::GRID_CELL_MINUTES;
    int cells = (maxFinish - minStart + Config::GRID_CELL_MINUTES - 1) / Config::GRID_CELL_MINUTES;

    // Time header
    cout << "       ";
    try {
        for (int i = 0; i < cells; i += 2)
            cout << left << setw(2) 
                 << TimeConverter::minutesToTime(minStart + i * Config::GRID_CELL_MINUTES);
        cout << "\n";

        // Activity bars
        for (const auto& a : acts) {
            cout << ConsoleStyle::CYAN << left << setw(7) 
                 << a.name.substr(0, 6) << ConsoleStyle::RESET;
            int startCell = (a.start - minStart) / Config::GRID_CELL_MINUTES;
            int endCell   = (a.finish - minStart + Config::GRID_CELL_MINUTES - 1) 
                           / Config::GRID_CELL_MINUTES;
            for (int i = 0; i < cells; ++i) {
                if (i >= startCell && i < endCell) 
                    cout << ConsoleStyle::GREEN << "█" << ConsoleStyle::RESET;
                else cout << "·";
            }
            cout << "\n";
        }
    } catch (const exception& e) {
        Logger::log(Logger::ERROR, "Grid display error: " + string(e.what()));
    }
}

// =============================================================================
//                    IMPROVED INPUT HANDLERS WITH VALIDATION
// =============================================================================

vector<Activity> getSampleData() {
    // IMPROVEMENT #9: Safer data initialization with try-catch
    vector<Activity> acts;
    try {
        acts.reserve(10);  // Preallocate
        acts.emplace_back(1,  "Math",      540,  600, 5, 720);      // 09:00-10:00
        acts.emplace_back(2,  "Physics",   600,  690, 4, 720);      // 10:00-11:30
        acts.emplace_back(3,  "Chemistry", 570,  660, 3, 690);      // 09:30-11:00
        acts.emplace_back(4,  "CS-Lab",    660,  780, 5, 840);      // 11:00-13:00
        acts.emplace_back(5,  "English",   690,  750, 2, 810);      // 11:30-12:30
        acts.emplace_back(6,  "DSA",       780,  870, 5, 900);      // 13:00-14:30
        acts.emplace_back(7,  "Sports",    840,  900, 1, 960);      // 14:00-15:00
        acts.emplace_back(8,  "Library",   900,  990, 3, 1020);     // 15:00-16:30
        acts.emplace_back(9,  "Workshop",  960, 1080, 4, 1080);     // 16:00-18:00
        acts.emplace_back(10, "Seminar",   870,  960, 4,  990);     // 14:30-16:00
    } catch (const exception& e) {
        Logger::log(Logger::ERROR, "Failed to load sample data: " + string(e.what()));
    }
    return acts;
}

vector<Activity> getUserInput() {
    // IMPROVEMENT #10: Comprehensive input validation and error handling
    int n;
    cout << ConsoleStyle::CYAN << "\nEnter number of activities: " << ConsoleStyle::RESET;
    if (!(cin >> n)) {
        Logger::log(Logger::ERROR, "Invalid input");
        cin.clear();
        cin.ignore(10000, '\n');
        return {};
    }
    
    if (n <= 0 || n > 100) {
        Logger::log(Logger::WARN, "Activity count should be 1-100. Got: " + to_string(n));
        return {};
    }

    vector<Activity> acts;
    acts.reserve(n);
    
    string startStr, finishStr, dlStr;
    
    for (int i = 0; i < n; ++i) {
        try {
            cout << ConsoleStyle::YELLOW << "\n--- Activity " << (i + 1) << " ---\n" 
                 << ConsoleStyle::RESET;
            
            string name;
            cout << "  Name (max 20 chars): ";
            cin >> name;
            if (name.length() > 20) name = name.substr(0, 20);
            
            cout << "  Start time (HH:MM): ";
            cin >> startStr;
            
            cout << "  Finish time (HH:MM): ";
            cin >> finishStr;
            
            int weight;
            cout << "  Priority (1-10): ";
            cin >> weight;
            
            cout << "  Deadline (HH:MM): ";
            cin >> dlStr;

            int start = TimeConverter::timeToMinutes(startStr);
            int finish = TimeConverter::timeToMinutes(finishStr);
            int deadline = TimeConverter::timeToMinutes(dlStr);

            // Activity constructor will validate
            acts.emplace_back(i + 1, name, start, finish, weight, deadline);
            Logger::log(Logger::INFO, "Added activity: " + name);
            
        } catch (const exception& e) {
            Logger::log(Logger::ERROR, "Activity " + to_string(i+1) + " error: " + 
                       string(e.what()));
            --i;  // Retry this activity
        }
    }
    
    return acts;
}

// =============================================================================
//                         IMPROVED MAIN ANALYSIS FLOW
// =============================================================================
void runFullAnalysis(vector<Activity> acts) {
    printHeader("INPUT ACTIVITIES");
    displayActivities(acts, "All Activities (Original)");

    // -------- Algorithm 1 ------------------------------------------------
    printHeader("1. ACTIVITY SELECTION (Maximize count - Earliest Finish Time)");
    auto sel1 = activitySelection(acts);
    displayActivities(sel1, "Selected Activities (Greedy by Finish Time)");
    cout << ConsoleStyle::GREEN << "\n  Total selected: " << sel1.size() << "/" << acts.size()
         << ConsoleStyle::RESET << "\n";
    displayTimetableGrid(sel1);

    // -------- Algorithm 2 ------------------------------------------------
    printHeader("2. PRIORITY-BASED WEIGHTED SCHEDULING");
    auto sel2 = weightedScheduling(acts);
    int totalWeight = 0;
    for (const auto& a : sel2) totalWeight += a.weight;
    displayActivities(sel2, "Selected Activities (Greedy by Priority)");
    cout << ConsoleStyle::GREEN << "\n  Total priority score: " << totalWeight 
         << ConsoleStyle::RESET << "\n";

    // -------- Algorithm 3 ------------------------------------------------
    printHeader("3. JOB SEQUENCING WITH DEADLINES (DSU Optimized)");
    auto sel3 = jobSequencingDSU(acts);
    int totalProfit = 0;
    for (const auto& a : sel3) totalProfit += a.weight;
    displayActivities(sel3, "Scheduled Jobs (Maximize Profit before Deadlines)");
    cout << ConsoleStyle::GREEN << "\n  Total profit: " << totalProfit 
         << ConsoleStyle::RESET << "\n";

    // -------- Algorithm 4 ------------------------------------------------
    printHeader("4. MINIMUM ROOMS REQUIRED (Meeting Rooms II)");
    vector<vector<Activity>> rooms;
    int roomCount = minRoomsRequired(acts, rooms);
    cout << ConsoleStyle::BOLD << ConsoleStyle::GREEN 
         << "  Minimum rooms required to fit ALL activities: "
         << roomCount << ConsoleStyle::RESET << "\n";
    displayRoomAssignment(rooms);

    // -------- Summary -----------------------------------------------------
    printHeader("COMPARATIVE SUMMARY");
    cout << ConsoleStyle::BOLD
         << left << setw(40) << "Algorithm"
         << setw(15) << "Selected"
         << setw(15) << "Score" << ConsoleStyle::RESET << "\n";
    cout << string(70, '-') << "\n";
    cout << left << setw(40) << "Activity Selection (Max Count)"
         << setw(15) << sel1.size() << setw(15) << "-" << "\n";
    cout << left << setw(40) << "Priority-based Greedy"
         << setw(15) << sel2.size() << setw(15) << totalWeight << "\n";
    cout << left << setw(40) << "Job Sequencing (DSU)"
         << setw(15) << sel3.size() << setw(15) << totalProfit << "\n";
    cout << left << setw(40) << "Min Rooms (all scheduled)"
         << setw(15) << acts.size() << setw(15) << roomCount << " rooms\n";
}

// IMPROVEMENT #11: Main function with error handling and removed competitive programming style
int main() {
    // IMPROVEMENT #12: Remove fastio - it's an anti-pattern for real applications
    // (competitive programming optimization, not best practice for production)
    
    try {
        cout << ConsoleStyle::BOLD << ConsoleStyle::CYAN << R"(
╔═══════════════════════════════════════════════════════════════════════════╗
║          GREEDY-BASED SCHEDULING / TIMETABLE SYSTEM (C++17)               ║
║          Algorithms: Activity Selection | Job Sequencing | Min-Heap        ║
║                      DSU-Optimized | Sweep Line | Priority Queue           ║
╚═══════════════════════════════════════════════════════════════════════════╝
)" << ConsoleStyle::RESET;

        while (true) {
            cout << "\n" << ConsoleStyle::BOLD << ConsoleStyle::YELLOW
                 << "MENU:\n"
                 << "  1. Run with sample university timetable\n"
                 << "  2. Enter custom activities\n"
                 << "  3. Exit\n"
                 << ConsoleStyle::RESET
                 << "Choice: ";
            int choice;
            if (!(cin >> choice)) {
                Logger::log(Logger::ERROR, "Invalid input");
                cin.clear();
                cin.ignore(10000, '\n');
                continue;
            }

            if (choice == 1) {
                runFullAnalysis(getSampleData());
            } else if (choice == 2) {
                auto acts = getUserInput();
                if (!acts.empty()) {
                    runFullAnalysis(acts);
                } else {
                    Logger::log(Logger::WARN, "No activities provided");
                }
            } else if (choice == 3) {
                cout << ConsoleStyle::GREEN << "Exiting. Goodbye!\n" 
                     << ConsoleStyle::RESET;
                break;
            } else {
                Logger::log(Logger::WARN, "Invalid choice. Please try again.");
            }
        }
    } catch (const exception& e) {
        Logger::log(Logger::ERROR, "Unhandled exception: " + string(e.what()));
        return 1;
    }
    return 0;
}
