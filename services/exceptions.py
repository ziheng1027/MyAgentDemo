class ToolError(Exception):
    """工具异常基类"""
    type = "tool_error"
    retry = False


class ToolParameterError(ToolError):
    """工具参数异常"""
    type = "parameter_error"
    retry = False


class ToolTimeoutError(ToolError):
    """工具超时异常"""
    type = "timeout_error"
    retry = True


class ToolServiceError(ToolError):
    """工具服务异常"""
    type = "service_error"
    retry = True