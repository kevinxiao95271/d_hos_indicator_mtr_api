package com.hospital.indicator.mapper.shard;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.hospital.indicator.entity.shard.ShardTask;
import org.apache.ibatis.annotations.Mapper;

/**
 * 分片任务 Mapper
 *
 * @author Claude
 * @date 2026-08-09
 */
@Mapper
public interface ShardTaskMapper extends BaseMapper<ShardTask> {
}
