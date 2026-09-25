from enum import Enum


class RunStatus(str, Enum):
    PENDING = "pending"
    PLANNING = "planning"
    CODING = "coding"
    EXECUTING = "executing"
    DEBUGGING = "debugging"
    VERIFIED = "verified"
    FAILED = "failed"


class ErrorType(str, Enum):
    NONE = "none"
    SYNTAX = "syntax"
    RUNTIME = "runtime"
    DEPENDENCY = "dependency"
    EMPTY_CODE = "empty_code"
    TIMEOUT = "timeout"
    PERMISSION = "permission"
    UNKNOWN = "unknown"


class ExecutionMode(str, Enum):
    SCRIPT = "script"
