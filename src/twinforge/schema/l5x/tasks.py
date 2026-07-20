from .spec import AttributeSpec, ElementSpec


TASK_ATTRIBUTES: dict[str, AttributeSpec] = {
    "Name": AttributeSpec(
        name="Name", description="Name of the task.", required=True, l5x_only=True,
        manual_ref="1756-RM014D-EN-P September 2025, Task attributes.",
    ),
    "Type": AttributeSpec(
        name="Type", description="Execution type of the task.", required=True,
        valid_values=("CONTINUOUS", "PERIODIC", "EVENT"),
        manual_ref="1756-RM014D-EN-P September 2025, Task attributes.",
    ),
    "Rate": AttributeSpec(
        name="Rate", description="Periodic task execution rate in milliseconds.",
        datatype=int, applicable_when=(("Type", ("PERIODIC",)),),
        manual_ref="1756-RM014D-EN-P September 2025, Task attributes.",
    ),
    "Priority": AttributeSpec(
        name="Priority", description="Scheduling priority of the task.", datatype=int,
        minimum=1, maximum=15,
        manual_ref="1756-RM014D-EN-P September 2025, Task attributes.",
    ),
    "Watchdog": AttributeSpec(
        name="Watchdog", description="Task watchdog timeout in milliseconds.", datatype=int,
        manual_ref="1756-RM014D-EN-P September 2025, Task attributes.",
    ),
    "DisableUpdateOutputs": AttributeSpec(
        name="DisableUpdateOutputs", description="Disables output updates when the task completes.",
        xml_type=str, datatype=bool, valid_values=("true", "false"),
        manual_ref="1756-RM014D-EN-P September 2025, Task attributes.",
    ),
    "InhibitTask": AttributeSpec(
        name="InhibitTask", description="Indicates whether execution of the task is inhibited.",
        xml_type=str, datatype=bool, valid_values=("true", "false"),
        manual_ref="1756-RM014D-EN-P September 2025, Task attributes.",
    ),
    "EventTrigger": AttributeSpec(
        name="EventTrigger", description="Trigger configuration for an event task.",
        applicable_when=(("Type", ("EVENT",)),),
        manual_ref="1756-RM014D-EN-P September 2025, Task attributes.",
    ),
}

SCHEDULED_PROGRAM_ATTRIBUTES: dict[str, AttributeSpec] = {
    "Name": AttributeSpec(
        name="Name", description="Name of a program scheduled by the task.", required=True,
        manual_ref="1756-RM014D-EN-P September 2025, Task structure.",
    ),
}

SCHEDULED_PROGRAMS_ELEMENTS: dict[str, ElementSpec] = {
    "ScheduledProgram": ElementSpec(
        name="ScheduledProgram", description="Reference to a program executed by the task.",
        attributes=SCHEDULED_PROGRAM_ATTRIBUTES, repeatable=True,
        manual_ref="1756-RM014D-EN-P September 2025, Task structure.",
    ),
}

TASK_ELEMENTS: dict[str, ElementSpec] = {
    "Description": ElementSpec(
        name="Description", description="User description of the task.", content_type="cdata",
        manual_ref="1756-RM014D-EN-P September 2025, Task structure.",
    ),
    "ScheduledPrograms": ElementSpec(
        name="ScheduledPrograms", description="Programs executed by the task in schedule order.",
        elements=SCHEDULED_PROGRAMS_ELEMENTS,
        manual_ref="1756-RM014D-EN-P September 2025, Task structure.",
    ),
}

TASKS_ELEMENTS: dict[str, ElementSpec] = {
    "Task": ElementSpec(
        name="Task", description="A controller execution task.", attributes=TASK_ATTRIBUTES,
        elements=TASK_ELEMENTS, repeatable=True,
        manual_ref="1756-RM014D-EN-P September 2025, Task structure.",
    ),
}
