package com.hospital.indicator.controller;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.hospital.indicator.common.BusinessException;
import com.hospital.indicator.common.ErrorCode;
import com.hospital.indicator.common.Result;
import com.hospital.indicator.context.UserContext;
import com.hospital.indicator.entity.sys.User;
import com.hospital.indicator.service.sys.UserService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@Tag(name = "用户管理")
@RestController
@RequestMapping("/system/user")
public class UserController {

    @Autowired
    private UserService userService;

    @Operation(summary = "获取用户列表（按科室筛选）")
    @GetMapping("/list")
    public Result<List<User>> list(@RequestParam(required = false) Long deptId) {
        List<User> users = userService.list(new LambdaQueryWrapper<User>()
                .eq(deptId != null, User::getDeptId, deptId)
                .orderByAsc(User::getUserId));
        return Result.success(users);
    }

    @Operation(summary = "保存/更新用户")
    @PostMapping("/save")
    public Result<Boolean> save(@RequestBody User user) {
        return Result.success(userService.saveOrUpdate(user));
    }

    @Operation(summary = "删除用户（仅超管）", description = "根据用户ID删除用户，不能删除自身")
    @DeleteMapping("/{userId}")
    public Result<Void> delete(
            @Parameter(description = "用户ID") @PathVariable Long userId) {
        requireAdmin();
        UserContext ctx = UserContext.get();
        if (ctx != null && userId.equals(ctx.getUserId())) {
            throw new BusinessException(ErrorCode.PARAM_INVALID, "不能删除当前登录用户本身");
        }
        User user = userService.getById(userId);
        if (user == null) {
            throw new BusinessException(ErrorCode.NOT_FOUND, "用户不存在，id=" + userId);
        }
        userService.removeById(userId);
        return Result.success("删除成功", null);
    }

    private void requireAdmin() {
        UserContext ctx = UserContext.get();
        if (ctx == null || ctx.getDataScope() == null || ctx.getDataScope() != 50) {
            throw new BusinessException(ErrorCode.FORBIDDEN, "无权限：仅超级管理员可执行此操作");
        }
    }
}
