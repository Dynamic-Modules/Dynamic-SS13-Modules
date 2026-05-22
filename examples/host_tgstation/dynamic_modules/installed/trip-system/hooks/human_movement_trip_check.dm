// This file demonstrates a normal hook implementation. A host-owned hook point
// would call into this proc instead of requiring a patch.
/proc/dynamic_module_trip_system_movement_hook(mob/living/carbon/human/user)
	if(!user)
		return

