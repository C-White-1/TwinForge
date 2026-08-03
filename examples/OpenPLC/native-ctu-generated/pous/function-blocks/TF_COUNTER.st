FUNCTION_BLOCK TF_COUNTER
VAR_INPUT
	CU : bool;
	CD : bool;
	RESET : bool;
	PV : dint;
	INITIAL_ACC : dint;
	INITIAL_DN : bool;
	INITIAL_OV : bool;
	INITIAL_UN : bool;
	UP_FIRST : bool;
END_VAR

VAR_OUTPUT
	Q : bool;
	CV : dint;
	CUEnabled : bool;
	CDEnabled : bool;
	OV : bool;
	UN : bool;
END_VAR

VAR
	WasCU : bool := FALSE;
	WasCD : bool := FALSE;
	UpEdge : bool := FALSE;
	DownEdge : bool := FALSE;
	Initialized : bool := FALSE;
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