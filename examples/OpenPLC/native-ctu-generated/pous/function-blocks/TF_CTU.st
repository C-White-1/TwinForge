FUNCTION_BLOCK TF_CTU
VAR_INPUT
	CU : bool;
	RESET : bool;
	PV : dint;
END_VAR

VAR_OUTPUT
	Q : bool;
	CV : dint;
	CountEnabled : bool;
	OV : bool;
END_VAR

VAR
	WasCU : bool := FALSE;
END_VAR

CountEnabled := CU;

IF RESET THEN
    CV := 0;
    Q := FALSE;
    OV := FALSE;
    CountEnabled := FALSE;
    WasCU := FALSE;
ELSE
    IF CU AND NOT WasCU THEN
        IF CV = 2147483647 THEN
            CV := -2147483647 - 1;
            OV := TRUE;
        ELSE
            CV := CV + 1;
        END_IF;
        IF CV >= PV THEN
            Q := TRUE;
        END_IF;
    END_IF;
    WasCU := CU;
END_IF;

END_FUNCTION_BLOCK