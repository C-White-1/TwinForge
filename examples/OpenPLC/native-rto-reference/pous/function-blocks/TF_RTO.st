FUNCTION_BLOCK TF_RTO
VAR_INPUT
    IN : BOOL;
    RESET : BOOL;
    PT : TIME;
END_VAR

VAR_OUTPUT
    Q : BOOL;
    ET : TIME;
    Enabled : BOOL;
    TT : BOOL;
END_VAR

VAR
    SegmentTimer : TON;
    RetainedTime : TIME := T#0s;
    RemainingTime : TIME := T#0s;
    WasEnabled : BOOL := FALSE;
END_VAR

Enabled := IN;

IF RESET THEN
    SegmentTimer(IN := FALSE, PT := T#0s);

    RetainedTime := T#0s;
    RemainingTime := T#0s;
    ET := T#0s;
    Q := FALSE;
    Enabled := FALSE;
    TT := FALSE;
    WasEnabled := FALSE;

ELSIF IN AND NOT Q THEN
    IF RetainedTime >= PT THEN
        RetainedTime := PT;
        ET := PT;
        Q := TRUE;
        TT := FALSE;
        SegmentTimer(IN := FALSE, PT := T#0s);
    ELSE
        RemainingTime := PT - RetainedTime;
        SegmentTimer(IN := TRUE, PT := RemainingTime);
        ET := RetainedTime + SegmentTimer.ET;

        IF SegmentTimer.Q THEN
            RetainedTime := PT;
            ET := PT;
            Q := TRUE;
        END_IF;

        TT := NOT Q;
    END_IF;

ELSIF NOT IN THEN
    IF WasEnabled AND NOT Q THEN
        RetainedTime := RetainedTime + SegmentTimer.ET;

        IF RetainedTime >= PT THEN
            RetainedTime := PT;
            Q := TRUE;
        END_IF;
    END_IF;

    SegmentTimer(IN := FALSE, PT := T#0s);
    ET := RetainedTime;
    TT := FALSE;

ELSE
    (* IN remains true after the timer has completed. *)
    SegmentTimer(IN := FALSE, PT := T#0s);
    ET := RetainedTime;
    TT := FALSE;
END_IF;

WasEnabled := IN;

END_FUNCTION_BLOCK