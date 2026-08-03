FUNCTION_BLOCK TF_COUNTER
VAR_INPUT
    CU : BOOL;
    CD : BOOL;
    RESET : BOOL;
    PV : DINT;
    INITIAL_ACC : DINT;
    INITIAL_DN : BOOL;
    INITIAL_OV : BOOL;
    INITIAL_UN : BOOL;
    UP_FIRST : BOOL;
END_VAR

VAR_OUTPUT
    Q : BOOL;
    CV : DINT;
    CUEnabled : BOOL;
    CDEnabled : BOOL;
    OV : BOOL;
    UN : BOOL;
END_VAR

VAR
    WasCU : BOOL := FALSE;
    WasCD : BOOL := FALSE;
    UpEdge : BOOL := FALSE;
    DownEdge : BOOL := FALSE;
    Initialized : BOOL := FALSE;
END_VAR

IF NOT Initialized THEN
    CV := INITIAL_ACC;
    Q := INITIAL_DN;
    OV := INITIAL_OV;
    UN := INITIAL_UN;
    WasCU := CU;
    WasCD := CD;
    Initialized := TRUE;
END_IF;

CUEnabled := CU;
CDEnabled := CD;
UpEdge := CU AND NOT WasCU;
DownEdge := CD AND NOT WasCD;

IF RESET THEN
    CV := 0;
    Q := FALSE;
    OV := FALSE;
    UN := FALSE;
    CUEnabled := FALSE;
    CDEnabled := FALSE;
    WasCU := FALSE;
    WasCD := FALSE;
ELSE
    IF UP_FIRST THEN
        IF UpEdge THEN
            IF CV = 2147483647 THEN
                CV := -2147483647 - 1;
                OV := TRUE;
            ELSE
                CV := CV + 1;
            END_IF;
        END_IF;
        IF DownEdge THEN
            IF CV = -2147483647 - 1 THEN
                CV := 2147483647;
                UN := TRUE;
            ELSE
                CV := CV - 1;
            END_IF;
        END_IF;
    ELSE
        IF DownEdge THEN
            IF CV = -2147483647 - 1 THEN
                CV := 2147483647;
                UN := TRUE;
            ELSE
                CV := CV - 1;
            END_IF;
        END_IF;
        IF UpEdge THEN
            IF CV = 2147483647 THEN
                CV := -2147483647 - 1;
                OV := TRUE;
            ELSE
                CV := CV + 1;
            END_IF;
        END_IF;
    END_IF;
    IF UpEdge OR DownEdge THEN
        Q := CV >= PV;
    END_IF;
    WasCU := CU;
    WasCD := CD;
END_IF;

END_FUNCTION_BLOCK
