import React, { useState } from "react";
import type { SchoolProfile } from "../types";

export const SetupFormComponent: React.FC<{
  profile: SchoolProfile;
  onChange: (profile: SchoolProfile) => void;
}> = ({ profile, onChange }) => {
  return (
    <div className="rounded-lg bg-white p-6 shadow">
      <h3 className="mb-4 text-lg font-semibold">Institution Setup</h3>
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium">Institution Name</label>
          <input
            type="text"
            value={profile.institution_name}
            onChange={(e) =>
              onChange({ ...profile, institution_name: e.target.value })
            }
            className="mt-1 w-full"
          />
        </div>
        <div>
          <label className="block text-sm font-medium">Student Count</label>
          <input
            type="number"
            value={profile.student_count}
            onChange={(e) => onChange({ ...profile, student_count: +e.target.value })}
            className="mt-1 w-full"
            min="1"
          />
        </div>
        <div>
          <label className="block text-sm font-medium">Days per Week</label>
          <input
            type="number"
            value={profile.days_per_week}
            onChange={(e) => onChange({ ...profile, days_per_week: +e.target.value })}
            className="mt-1 w-full"
            min="3"
            max="7"
          />
        </div>
        <div>
          <label className="block text-sm font-medium">Periods per Day</label>
          <input
            type="number"
            value={profile.periods_per_day}
            onChange={(e) => onChange({ ...profile, periods_per_day: +e.target.value })}
            className="mt-1 w-full"
            min="3"
            max="12"
          />
        </div>
        <div>
          <label className="block text-sm font-medium">Core Subjects Target</label>
          <input
            type="number"
            value={profile.core_subjects_target}
            onChange={(e) =>
              onChange({ ...profile, core_subjects_target: +e.target.value })
            }
            className="mt-1 w-full"
            min="1"
            max="15"
          />
        </div>
        <div>
          <label className="block text-sm font-medium">Elective Limit</label>
          <input
            type="number"
            value={profile.elective_limit}
            onChange={(e) => onChange({ ...profile, elective_limit: +e.target.value })}
            className="mt-1 w-full"
            min="0"
            max="20"
          />
        </div>
      </div>
    </div>
  );
};
