/datum/dynamic_module_trip_system
	var/trip_chance = 5

/datum/dynamic_module_trip_system/proc/check_trip(mob/living/carbon/human/user)
	if(!user)
		return FALSE
	return prob(trip_chance)

