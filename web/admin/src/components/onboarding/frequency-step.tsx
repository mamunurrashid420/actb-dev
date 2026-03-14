"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { cn } from "@/lib/utils";

const frequencyOptions = ["Daily", "Weekly", "Monthly", "Quarterly", "Rarely", "Never"];

interface FrequencyStepProps {
  onContinue?: (frequency: string) => void;
  onBack?: () => void;
  progress?: number;
}

export function FrequencyStep({
  onContinue,
  onBack,
  progress = 66,
}: FrequencyStepProps) {
  const [selectedFrequency, setSelectedFrequency] = useState<string | null>(null);

  const handleContinue = () => {
    if (selectedFrequency && onContinue) {
      onContinue(selectedFrequency);
    }
  };

  return (
    <div className="bg-card relative flex size-full max-w-[680px] flex-col gap-6 rounded-xl border p-7 shadow-sm">
      <div className="shrink-0">
        <div className="bg-muted relative h-2 w-36 overflow-hidden rounded-full">
          <div
            className="bg-primary absolute left-0 top-0 h-full rounded-full transition-all duration-300"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>

      <div className="w-full max-w-[500px] space-y-1.5">
        <h2 className="text-card-foreground text-2xl font-semibold leading-snug">
          How often do you check
          <br />
          your business performance?
        </h2>
        <p className="text-muted-foreground text-sm leading-relaxed">
          This helps us understand your needs and tailor the experience to your
          workflow.
        </p>
      </div>

      <RadioGroup
        value={selectedFrequency ?? ""}
        onValueChange={(value) => setSelectedFrequency(value)}
        className="grid grid-cols-2 gap-2.5 md:grid-cols-3"
      >
        {frequencyOptions.map((option) => {
          const id = `freq-${option.toLowerCase()}`;
          const isSelected = selectedFrequency === option;
          return (
            <label
              key={option}
              htmlFor={id}
              className={cn(
                "bg-card text-card-foreground hover:border-primary/60 flex cursor-pointer items-center gap-2.5 rounded-md border px-3 py-2.5 text-sm font-medium transition-colors",
                isSelected ? "border-primary bg-primary/5 shadow-xs" : "border-border",
              )}
            >
              <RadioGroupItem id={id} value={option} className="mt-0.5" />
              <span>{option}</span>
            </label>
          );
        })}
      </RadioGroup>

      <div className="mt-auto flex items-center justify-end gap-3 pt-1.5">
        <Button
          type="button"
          variant="ghost"
          onClick={onBack}
          className="text-muted-foreground hover:text-foreground h-10 px-3 text-sm"
        >
          Back
        </Button>
        <Button
          type="button"
          onClick={handleContinue}
          disabled={!selectedFrequency}
          className="bg-primary text-primary-foreground hover:bg-primary/90 shadow-xs h-10 min-w-[120px] rounded-md px-4 text-sm font-medium transition-all hover:shadow-sm disabled:opacity-50"
        >
          Continue
        </Button>
      </div>
    </div>
  );
}
